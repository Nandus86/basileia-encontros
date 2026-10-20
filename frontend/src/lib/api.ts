import type {
  ContaDeTeste, Conteudo, Denuncia, DetalheDaConexao, Devocional, EventoDaDupla, ItemDeRevelacao, Jornada,
  MensagemChat, MeuPerfil, Publico, ResumoDaConexao, ResumoDoTeste, Sinal, Teste,
} from "@/types";

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

async function chamar<T>(caminho: string, opcoes: RequestInit = {}, chaveLider?: string): Promise<T> {
  const headers = new Headers(opcoes.headers);
  if (tokenAtual && !chaveLider) headers.set("Authorization", `Bearer ${tokenAtual}`);
  if (chaveLider) headers.set("X-Chave-Lider", chaveLider);
  if (opcoes.body && !(opcoes.body instanceof FormData)) headers.set("Content-Type", "application/json");
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${caminho}`, { ...opcoes, headers });
  } catch {
    throw new ErroDaApi("Sem conexão. Confira a internet e tente de novo.", 0);
  }
  if (res.status === 401 && tokenAtual && !chaveLider) {
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
const post = (corpo?: unknown): RequestInit => ({ method: "POST", body: corpo === undefined ? undefined : json(corpo) });

export type ResultadoEntrada =
  | { token: string; perfil: MeuPerfil }
  | { escolher: { igreja_id: string; igreja_nome: string }[] };

type ComJornada<T> = T & Jornada;

export const api = {
  entrar: (usuario: string, senha: string, igreja_id?: string) =>
    chamar<ResultadoEntrada>("/entrar", post({ usuario, senha, igreja_id })),
  contasDeTeste: () => chamar<ContaDeTeste[]>("/demo/contas"),
  saude: () => chamar<{ ok: boolean; demo: boolean }>("/saude"),
  hobbies: () => chamar<{ hobbies: string[]; minimo: number }>("/hobbies"),

  eu: () => chamar<MeuPerfil>("/eu"),
  mudarEu: (campos: Partial<Pick<MeuPerfil, "hobbies" | "bio" | "idade_min" | "idade_max" | "raio_km" | "visivel">>) =>
    chamar<MeuPerfil>("/eu", { method: "PUT", body: json(campos) }),
  mudarRevelacoes: (limites: Partial<Record<ItemDeRevelacao, number | null>>) =>
    chamar<MeuPerfil>("/eu/revelacoes", { method: "PUT", body: json({ limites }) }),
  mudarLocal: (lat: number, lon: number) => chamar<MeuPerfil>("/eu/localizacao", post({ lat, lon })),
  mandarFoto: (arquivo: Blob) => {
    const dados = new FormData();
    dados.append("foto", arquivo, "foto.jpg");
    return chamar<MeuPerfil>("/eu/foto", { method: "POST", body: dados });
  },

  sinais: () => chamar<{ pronto: boolean; sinais: Sinal[]; demo: boolean }>("/sinais"),
  responderSinal: (para_id: number, enviar: boolean) =>
    chamar<{ conexao: { id: number; pontos: number; outra: Publico } | null }>("/sinais", post({ para_id, enviar })),
  maisSinais: () => chamar<{ ok: true }>("/sinais/mais", post()),

  conexoes: () => chamar<ResumoDaConexao[]>("/conexoes"),
  conexao: (id: number) => chamar<DetalheDaConexao>(`/conexoes/${id}`),
  liberar: (id: number, item: ItemDeRevelacao) => chamar<{ ok: true }>(`/conexoes/${id}/liberar`, post({ item })),
  responderPergunta: (id: number, texto: string) =>
    chamar<{ evento: EventoDaDupla | null }>(`/conexoes/${id}/pergunta`, post({ texto })),
  mensagens: (id: number, depois_de = 0) =>
    chamar<{ mensagens: MensagemChat[] }>(`/conexoes/${id}/mensagens?depois_de=${depois_de}`),
  enviar: (id: number, texto: string) => chamar<MensagemChat>(`/conexoes/${id}/mensagens`, post({ texto })),
  marcarLido: (id: number, ate: number) => chamar<{ ok: true }>(`/conexoes/${id}/lido`, post({ ate })),
  desfazer: (id: number) => chamar<{ ok: true }>(`/conexoes/${id}`, { method: "DELETE" }),
  denunciar: (pessoa_id: number, motivo: string) => chamar<{ ok: true }>("/denuncias", post({ pessoa_id, motivo })),

  jornada: () =>
    chamar<ComJornada<{ devocional: Devocional | null; testes: ResumoDoTeste[] }>>("/jornada"),
  fazerDevocional: (texto: string) => chamar<ComJornada<{ ganhou: number }>>("/jornada/devocional", post({ texto })),
  teste: (id: number) => chamar<Teste>(`/jornada/testes/${id}`),
  fazerTeste: (id: number, escolhas: number[]) =>
    chamar<ComJornada<{ ganhou: number }>>(`/jornada/testes/${id}`, post({ escolhas })),
};

/** Painel do líder: tudo vai com a chave dele, nunca com o token de membro. */
export const lider = {
  conferir: (chave: string) => chamar<{ ok: true }>("/lider/entrar", {}, chave),
  conteudos: (chave: string, status?: string) =>
    chamar<Conteudo[]>(`/lider/conteudos${status ? `?status=${status}` : ""}`, {}, chave),
  aprovar: (chave: string, id: number, dados?: Record<string, unknown>) =>
    chamar<Conteudo>(`/lider/conteudos/${id}/aprovar`, post({ dados }), chave),
  recusar: (chave: string, id: number) => chamar<Conteudo>(`/lider/conteudos/${id}/recusar`, post(), chave),
  criar: (chave: string, tipo: string, dados: Record<string, unknown>) =>
    chamar<Conteudo>("/lider/conteudos", post({ tipo, dados }), chave),
  gerar: (chave: string, tipo: string, quantidade: number) =>
    chamar<Conteudo[]>("/lider/gerar", post({ tipo, quantidade }), chave),
  denuncias: (chave: string) => chamar<Denuncia[]>("/lider/denuncias", {}, chave),
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
