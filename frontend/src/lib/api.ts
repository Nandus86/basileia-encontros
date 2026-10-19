import type { Cartao, ContaDeTeste, Match, MensagemChat, MeuPerfil } from "@/types";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8020";

export class NaoAutorizado extends Error {}

export class ErroDaApi extends Error {
  constructor(message: string, public status: number) {
    super(message);
  }
}

let tokenAtual: string | null = null;
let aoSair: (() => void) | null = null;

/** A sessão registra aqui o token e o que fazer quando ele vence (401). */
export function configurarSessao(token: string | null, quandoVencer: () => void) {
  tokenAtual = token;
  aoSair = quandoVencer;
}

async function chamar<T>(caminho: string, opcoes: RequestInit = {}): Promise<T> {
  const headers = new Headers(opcoes.headers);
  if (tokenAtual) headers.set("Authorization", `Bearer ${tokenAtual}`);
  if (opcoes.body && !(opcoes.body instanceof FormData)) headers.set("Content-Type", "application/json");
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${caminho}`, { ...opcoes, headers });
  } catch {
    throw new ErroDaApi("Sem conexão. Confira a internet e tente de novo.", 0);
  }
  if (res.status === 401 && tokenAtual) {
    aoSair?.();
    throw new NaoAutorizado();
  }
  if (!res.ok) {
    let detalhe = "Algo deu errado. Tente de novo.";
    try {
      const corpo = await res.json();
      if (typeof corpo?.detail === "string") detalhe = corpo.detail;
    } catch {}
    throw new ErroDaApi(detalhe, res.status);
  }
  return res.json() as Promise<T>;
}

const json = (corpo: unknown) => JSON.stringify(corpo);

export type ResultadoEntrada =
  | { token: string; perfil: MeuPerfil }
  | { escolher: { igreja_id: string; igreja_nome: string }[] };

export const api = {
  entrar: (usuario: string, senha: string, igreja_id?: string) =>
    chamar<ResultadoEntrada>("/entrar", { method: "POST", body: json({ usuario, senha, igreja_id }) }),
  contasDeTeste: () => chamar<ContaDeTeste[]>("/demo/contas"),
  saude: () => chamar<{ ok: boolean; demo: boolean }>("/saude"),
  hobbies: () => chamar<{ hobbies: string[]; minimo: number }>("/hobbies"),

  eu: () => chamar<MeuPerfil>("/eu"),
  mudarEu: (campos: Partial<Pick<MeuPerfil, "hobbies" | "bio" | "idade_min" | "idade_max" | "raio_km" | "visivel">>) =>
    chamar<MeuPerfil>("/eu", { method: "PUT", body: json(campos) }),
  mudarLocal: (lat: number, lon: number) =>
    chamar<MeuPerfil>("/eu/localizacao", { method: "POST", body: json({ lat, lon }) }),
  mandarFoto: (arquivo: Blob) => {
    const dados = new FormData();
    dados.append("foto", arquivo, "foto.jpg");
    return chamar<MeuPerfil>("/eu/foto", { method: "POST", body: dados });
  },

  descobrir: () => chamar<{ pronto: boolean; cartoes: Cartao[] }>("/descobrir"),
  reagir: (para_id: number, curtiu: boolean) =>
    chamar<{ match: { id: number; pessoa: Cartao } | null }>("/reacoes", {
      method: "POST",
      body: json({ para_id, curtiu }),
    }),

  matches: () => chamar<Match[]>("/matches"),
  match: (id: number) => chamar<Omit<Match, "ultima" | "nao_lidas">>(`/matches/${id}`),
  mensagens: (id: number, depois_de = 0) =>
    chamar<{ mensagens: MensagemChat[]; foto_liberada: boolean; eu_liberei: boolean }>(
      `/matches/${id}/mensagens?depois_de=${depois_de}`,
    ),
  enviar: (id: number, texto: string) =>
    chamar<MensagemChat>(`/matches/${id}/mensagens`, { method: "POST", body: json({ texto }) }),
  marcarLido: (id: number, ate: number) =>
    chamar<{ ok: true }>(`/matches/${id}/lido`, { method: "POST", body: json({ ate }) }),
  liberarFoto: (id: number) => chamar<{ ok: true }>(`/matches/${id}/liberar-foto`, { method: "POST" }),
  desfazer: (id: number) => chamar<{ ok: true }>(`/matches/${id}`, { method: "DELETE" }),
  denunciar: (pessoa_id: number, motivo: string) =>
    chamar<{ ok: true }>("/denuncias", { method: "POST", body: json({ pessoa_id, motivo }) }),
};

/** A foto não tem link público: vem com o token e vira um endereço local (blob:) só nesta aba. */
const fotos = new Map<number, Promise<string | null>>();

export function carregarFoto(pessoaId: number, recarregar = false): Promise<string | null> {
  if (recarregar) fotos.delete(pessoaId);
  if (!fotos.has(pessoaId)) {
    const pedido = fetch(`${API_BASE}/fotos/${pessoaId}`, {
      headers: tokenAtual ? { Authorization: `Bearer ${tokenAtual}` } : {},
    })
      .then(async (r) => (r.ok ? URL.createObjectURL(await r.blob()) : null))
      .catch(() => null);
    pedido.then((url) => {
      if (!url) fotos.delete(pessoaId);
    });
    fotos.set(pessoaId, pedido);
  }
  return fotos.get(pessoaId)!;
}

export function esquecerFotos() {
  fotos.forEach((p) => p.then((url) => url && URL.revokeObjectURL(url)));
  fotos.clear();
}
