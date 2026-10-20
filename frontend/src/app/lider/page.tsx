"use client";

import { useCallback, useEffect, useState } from "react";
import { Botao, Logo } from "@/components/estrutura";
import { IconeBrilho } from "@/components/icones";
import { lider } from "@/lib/api";
import type { Conteudo, Denuncia } from "@/types";

const CHAVE = "encontros:lider";
const TIPOS = { devocional: "Devocional", pergunta: "Pergunta a dois", teste: "Teste" } as const;
type Aba = "pendente" | "aprovado" | "gerar" | "denuncias";

function lerChave() {
  try {
    return sessionStorage.getItem(CHAVE) || "";
  } catch {
    return "";
  }
}

export default function PainelDoLider() {
  const [chave, setChave] = useState("");
  const [valida, setValida] = useState(false);
  const [digitada, setDigitada] = useState("");
  const [erro, setErro] = useState("");

  const entrar = useCallback(async (tentativa: string) => {
    setErro("");
    try {
      await lider.conferir(tentativa);
      try { sessionStorage.setItem(CHAVE, tentativa); } catch {}
      setChave(tentativa);
      setValida(true);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Chave incorreta.");
    }
  }, []);

  useEffect(() => {
    const guardada = lerChave();
    if (guardada) lider.conferir(guardada).then(() => { setChave(guardada); setValida(true); }).catch(() => {});
  }, []);

  if (!valida) {
    return (
      <div className="mx-auto flex min-h-dvh max-w-md flex-col justify-center px-5">
        <Logo />
        <h1 className="mt-8 text-2xl font-extrabold">Painel da liderança</h1>
        <p className="mt-2 text-texto-2">Aprovar devocionais, perguntas e testes antes de chegarem aos membros.</p>
        <form className="mt-6 space-y-3" onSubmit={(e) => { e.preventDefault(); entrar(digitada); }}>
          <input type="password" value={digitada} onChange={(e) => setDigitada(e.target.value)} placeholder="Chave do líder"
            aria-label="Chave do líder" className="h-13 w-full rounded-2xl border border-borda bg-superficie px-4 outline-none focus:border-primaria" />
          {erro && <p role="alert" className="text-sm text-perigo">{erro}</p>}
          <Botao type="submit" className="w-full">Entrar</Botao>
        </form>
      </div>
    );
  }
  return <Painel chave={chave} sair={() => { try { sessionStorage.removeItem(CHAVE); } catch {} setValida(false); }} />;
}

function Painel({ chave, sair }: { chave: string; sair: () => void }) {
  const [aba, setAba] = useState<Aba>("pendente");
  const [lista, setLista] = useState<Conteudo[]>([]);
  const [denuncias, setDenuncias] = useState<Denuncia[]>([]);
  const [aviso, setAviso] = useState<{ texto: string; erro: boolean } | null>(null);

  const carregar = useCallback(() => {
    if (aba === "pendente" || aba === "aprovado") lider.conteudos(chave, aba).then(setLista).catch(() => {});
    if (aba === "denuncias") lider.denuncias(chave).then(setDenuncias).catch(() => {});
  }, [aba, chave]);

  useEffect(carregar, [carregar]);

  async function acao(fazer: () => Promise<unknown>, ok: string) {
    setAviso(null);
    try {
      await fazer();
      setAviso({ texto: ok, erro: false });
      carregar();
    } catch (e) {
      setAviso({ texto: e instanceof Error ? e.message : "Não deu certo.", erro: true });
    }
  }

  return (
    <div className="mx-auto min-h-dvh max-w-2xl px-4 pt-[max(env(safe-area-inset-top),1rem)] pb-10">
      <div className="flex items-center justify-between">
        <Logo pequeno />
        <button type="button" onClick={sair} className="text-sm font-semibold text-texto-2">Sair</button>
      </div>
      <h1 className="mt-5 text-2xl font-extrabold">Painel da liderança</h1>
      <nav className="mt-4 flex gap-2 overflow-x-auto pb-1" role="tablist">
        {([["pendente", "Para aprovar"], ["aprovado", "Publicados"], ["gerar", "Gerar com IA"], ["denuncias", "Denúncias"]] as const).map(([a, rotulo]) => (
          <button key={a} type="button" role="tab" aria-selected={aba === a} onClick={() => { setAba(a); setAviso(null); }}
            className={`shrink-0 rounded-full px-4 py-2 text-sm font-bold ${aba === a ? "bg-primaria text-sobre-primaria" : "border border-borda bg-superficie"}`}>
            {rotulo}
          </button>
        ))}
      </nav>
      {aviso && <p role="status" className={`mt-4 rounded-xl px-4 py-3 text-sm font-medium ${aviso.erro ? "bg-perigo/10 text-perigo" : "bg-sucesso/10 text-sucesso"}`}>{aviso.texto}</p>}

      <div className="mt-4 space-y-3">
        {(aba === "pendente" || aba === "aprovado") && lista.length === 0 && (
          <p className="text-texto-2">{aba === "pendente" ? "Nada esperando aprovação. Gere novos conteúdos na aba “Gerar com IA”." : "Nada publicado ainda."}</p>
        )}
        {(aba === "pendente" || aba === "aprovado") && lista.map((c) => (
          <CartaoDeConteudo key={c.id} conteudo={c}
            aprovar={(dados) => acao(() => lider.aprovar(chave, c.id, dados), aba === "pendente" ? "Aprovado e publicado." : "Atualizado.")}
            recusar={() => acao(() => lider.recusar(chave, c.id), aba === "pendente" ? "Recusado." : "Retirado do app.")} />
        ))}
        {aba === "gerar" && <Gerar chave={chave} aoGerar={(n) => { setAviso({ texto: `${n} item(ns) gerado(s). Revise na aba “Para aprovar”.`, erro: false }); }} />}
        {aba === "denuncias" && (denuncias.length === 0 ? <p className="text-texto-2">Nenhuma denúncia.</p> : denuncias.map((d) => (
          <div key={d.id} className="rounded-2xl border border-borda bg-superficie p-4 text-sm">
            <p><strong>{d.de.nome}</strong> ({d.de.igreja}) denunciou <strong>{d.sobre.nome}</strong> ({d.sobre.igreja}, “{d.sobre.codinome}”)</p>
            <p className="mt-1 text-texto-2">{d.motivo || "Sem motivo escrito"} · {new Date(d.criado_em).toLocaleString("pt-BR")}</p>
          </div>
        )))}
      </div>
    </div>
  );
}

function CartaoDeConteudo({ conteudo, aprovar, recusar }: {
  conteudo: Conteudo; aprovar: (dados?: Record<string, unknown>) => void; recusar: () => void;
}) {
  const [editando, setEditando] = useState(false);
  const [texto, setTexto] = useState(() => JSON.stringify(conteudo.dados, null, 2));
  const [erro, setErro] = useState("");
  const d = conteudo.dados as Record<string, unknown> & { questoes?: { texto: string; opcoes: string[] }[] };

  function salvar() {
    try {
      aprovar(JSON.parse(texto));
      setEditando(false);
    } catch {
      setErro("O texto editado não é um JSON válido.");
    }
  }

  return (
    <article className="rounded-2xl border border-borda bg-superficie p-4">
      <div className="mb-2 flex items-center gap-2 text-xs font-bold">
        <span className="rounded-full bg-primaria/10 px-2.5 py-1 text-primaria">{TIPOS[conteudo.tipo]}</span>
        <span className="text-texto-2">{conteudo.origem === "ia" ? "gerado pela IA" : conteudo.origem === "semente" ? "conteúdo inicial" : "escrito pelo líder"}</span>
        {conteudo.dia && <span className="text-texto-2">· saiu em {conteudo.dia}</span>}
      </div>
      {editando ? (
        <textarea value={texto} onChange={(e) => setTexto(e.target.value)} rows={12} aria-label="Editar conteúdo"
          className="w-full rounded-xl border border-borda bg-fundo p-3 font-mono text-xs outline-none focus:border-primaria" />
      ) : conteudo.tipo === "pergunta" ? (
        <p className="text-lg font-bold">{String(d.texto)}</p>
      ) : conteudo.tipo === "devocional" ? (
        <div className="space-y-1">
          <p className="text-lg font-bold">{String(d.titulo)}</p>
          <p className="text-sm font-semibold text-primaria">{String(d.referencia)}</p>
          <p className="text-sm">{String(d.reflexao)}</p>
          <p className="text-sm font-semibold">Pergunta: {String(d.pergunta)}</p>
        </div>
      ) : (
        <div>
          <p className="text-lg font-bold">{String(d.titulo)}</p>
          <ol className="mt-2 list-decimal space-y-2 pl-5 text-sm">
            {(d.questoes || []).map((q) => (
              <li key={q.texto}><p className="font-semibold">{q.texto}</p><p className="text-texto-2">{q.opcoes.join(" · ")}</p></li>
            ))}
          </ol>
        </div>
      )}
      {erro && <p role="alert" className="mt-2 text-sm text-perigo">{erro}</p>}
      <div className="mt-3 flex flex-wrap gap-2">
        {editando ? (
          <>
            <Botao className="min-h-10 text-sm" onClick={salvar}>Salvar e aprovar</Botao>
            <Botao variante="fantasma" className="min-h-10 text-sm" onClick={() => setEditando(false)}>Cancelar</Botao>
          </>
        ) : (
          <>
            {conteudo.status === "pendente" && <Botao className="min-h-10 text-sm" onClick={() => aprovar()}>Aprovar</Botao>}
            <Botao variante="secundario" className="min-h-10 text-sm" onClick={() => setEditando(true)}>Editar</Botao>
            <Botao variante="perigo" className="min-h-10 text-sm" onClick={recusar}>{conteudo.status === "pendente" ? "Recusar" : "Retirar"}</Botao>
          </>
        )}
      </div>
    </article>
  );
}

function Gerar({ chave, aoGerar }: { chave: string; aoGerar: (n: number) => void }) {
  const [tipo, setTipo] = useState<keyof typeof TIPOS>("pergunta");
  const [quantidade, setQuantidade] = useState(3);
  const [gerando, setGerando] = useState(false);
  const [erro, setErro] = useState("");

  async function gerar() {
    setErro("");
    setGerando(true);
    try {
      aoGerar((await lider.gerar(chave, tipo, quantidade)).length);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "A IA não respondeu.");
    } finally {
      setGerando(false);
    }
  }

  return (
    <div className="space-y-4 rounded-2xl border border-borda bg-superficie p-4">
      <p className="text-sm text-texto-2">
        A IA escreve e tudo cai em “Para aprovar”. Nada chega aos membros sem a sua aprovação. Os testes são de visão e
        vivência (sem resposta certa) e evitam temas que dividem denominações.
      </p>
      <div className="flex flex-wrap gap-2">
        {(Object.keys(TIPOS) as (keyof typeof TIPOS)[]).map((t) => (
          <button key={t} type="button" onClick={() => setTipo(t)} aria-pressed={tipo === t}
            className={`rounded-full px-4 py-2 text-sm font-bold ${tipo === t ? "bg-primaria text-sobre-primaria" : "border border-borda"}`}>
            {TIPOS[t]}
          </button>
        ))}
      </div>
      <label className="flex items-center gap-3 text-sm font-semibold">
        Quantos
        <input type="number" min={1} max={5} value={quantidade} onChange={(e) => setQuantidade(Number(e.target.value))}
          className="h-10 w-20 rounded-xl border border-borda bg-fundo text-center outline-none focus:border-primaria" />
      </label>
      {erro && <p role="alert" className="text-sm text-perigo">{erro}</p>}
      <Botao onClick={gerar} disabled={gerando}><IconeBrilho className="size-5" /> {gerando ? "A IA está escrevendo…" : "Gerar"}</Botao>
    </div>
  );
}
