"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { Sintonia, TrilhaDePontos } from "@/components/afinidade";
import { Avatar } from "@/components/avatar";
import { Botao, Protegida } from "@/components/estrutura";
import { IconeBrilho, IconeCadeado, IconeCheck, IconeEnviar, IconeMais, IconeVoltar } from "@/components/icones";
import { api, ErroDaApi } from "@/lib/api";
import { nomeDe } from "@/lib/nomes";
import type { DetalheDaConexao, MensagemChat, MinhaRevelacao } from "@/types";

export default function Conexao() {
  return (
    <Protegida completo={false}>
      <Detalhe />
    </Protegida>
  );
}

function Detalhe() {
  const { id } = useParams<{ id: string }>();
  const conexaoId = Number(id);
  const router = useRouter();
  const [d, setD] = useState<DetalheDaConexao | null>(null);
  const [aba, setAba] = useState<"dois" | "chat">("dois");
  const [menu, setMenu] = useState(false);
  const [confirmar, setConfirmar] = useState<null | { tipo: "liberar"; r: MinhaRevelacao } | { tipo: "desfazer" | "denunciar" }>(null);
  const [verFoto, setVerFoto] = useState(false);
  const [aviso, setAviso] = useState("");

  const carregar = useCallback(() =>
    api.conexao(conexaoId).then(setD).catch((e) => {
      if (e instanceof ErroDaApi && e.status === 404) router.replace("/conexoes");
    }), [conexaoId, router]);

  useEffect(() => {
    carregar();
    const intervalo = setInterval(carregar, 15000);
    return () => clearInterval(intervalo);
  }, [carregar]);

  async function executar() {
    if (!confirmar || !d) return;
    try {
      if (confirmar.tipo === "liberar") await api.liberar(conexaoId, confirmar.r.item);
      if (confirmar.tipo === "desfazer") await api.desfazer(conexaoId);
      if (confirmar.tipo === "denunciar") await api.denunciar(d.outra.id, "Denúncia pela conexão");
      if (confirmar.tipo !== "liberar") return router.replace("/conexoes");
      await carregar();
    } catch (e) {
      setAviso(e instanceof Error ? e.message : "Não deu certo.");
    } finally {
      setConfirmar(null);
    }
  }

  if (!d) return <div className="flex min-h-dvh items-center justify-center"><div className="size-8 animate-spin rounded-full border-4 border-borda border-t-primaria" /></div>;
  const { outra } = d;
  const marcos = [
    ...(d.proxima_descoberta ? [{ pontos: d.proxima_descoberta.pontos, rotulo: d.proxima_descoberta.rotulo }] : []),
    ...(d.chat_abre_em ? [{ pontos: d.chat_abre_em, rotulo: "Chat" }] : []),
    ...d.minhas.filter((r) => r.limite && !r.na_mao).map((r) => ({ pontos: r.limite!, rotulo: r.rotulo })),
  ];

  return (
    <div className="mx-auto flex h-dvh max-w-md flex-col">
      <header className="border-b border-borda bg-superficie px-2 pt-[max(env(safe-area-inset-top),0.5rem)]">
        <div className="flex items-center gap-2 pb-2">
          <Link href="/conexoes" aria-label="Voltar" className="rounded-full p-2 hover:bg-superficie-2"><IconeVoltar /></Link>
          <button type="button" className="flex min-w-0 flex-1 items-center gap-3 text-left" disabled={!outra.foto}
            onClick={() => setVerFoto(true)} aria-label={outra.foto ? "Ver a foto" : undefined}>
            <Avatar id={outra.id} nome={outra.codinome} simbolo={outra.simbolo} liberada={outra.foto} tamanho={44} />
            <div className="min-w-0">
              <p className="truncate font-bold">{nomeDe(outra)}{outra.idade ? `, ${outra.idade}` : ""}</p>
              <div className="flex items-center gap-2"><Sintonia valor={d.sintonia} />
                {d.nivel_dela && <span className="text-xs text-texto-2">Nível {d.nivel_dela}</span>}</div>
            </div>
          </button>
          <div className="relative">
            <button type="button" onClick={() => setMenu(!menu)} aria-label="Mais opções" aria-expanded={menu}
              className="rounded-full p-2 hover:bg-superficie-2"><IconeMais /></button>
            {menu && (
              <div className="surgir absolute right-0 z-10 mt-1 w-52 overflow-hidden rounded-2xl border border-borda bg-superficie shadow-cartao">
                <button type="button" className="block w-full px-4 py-3 text-left hover:bg-superficie-2"
                  onClick={() => { setMenu(false); setConfirmar({ tipo: "desfazer" }); }}>Encerrar conexão</button>
                <button type="button" className="block w-full px-4 py-3 text-left text-perigo hover:bg-superficie-2"
                  onClick={() => { setMenu(false); setConfirmar({ tipo: "denunciar" }); }}>Denunciar</button>
              </div>
            )}
          </div>
        </div>
        <div className="flex" role="tablist">
          {(["dois", "chat"] as const).map((a) => (
            <button key={a} type="button" role="tab" aria-selected={aba === a} onClick={() => setAba(a)}
              className={`flex flex-1 items-center justify-center gap-1.5 border-b-2 py-2.5 text-sm font-bold ${
                aba === a ? "border-primaria text-primaria" : "border-transparent text-texto-2"}`}>
              {a === "dois" ? "A dois" : <>{!d.chat_aberto && <IconeCadeado className="size-4" />} Chat</>}
            </button>
          ))}
        </div>
      </header>

      {aviso && <p role="alert" className="mx-4 mt-3 rounded-xl bg-perigo/10 px-4 py-2 text-sm text-perigo">{aviso}</p>}

      {aba === "dois" ? (
        <main className="flex-1 space-y-4 overflow-y-auto px-4 py-4">
          <section className="rounded-3xl border border-borda bg-superficie p-4">
            <div className="flex items-baseline justify-between">
              <p className="rotulo flex-1">Afinidade</p>
              <span className="ml-3 text-3xl font-black text-primaria">{d.pontos}<span className="text-sm font-bold text-texto-2"> pts</span></span>
            </div>
            <TrilhaDePontos pontos={d.pontos} marcos={marcos} />
            <p className="text-sm text-texto-2">
              {d.chat_aberto ? "O chat está aberto para vocês." : d.chat_abre_em
                ? `O chat abre com ${d.chat_abre_em} pontos (o maior limite dos dois).` : "O chat abre quando os dois liberarem."}
              {d.proxima_descoberta && ` Com ${d.proxima_descoberta.pontos} você descobre: ${d.proxima_descoberta.rotulo.toLowerCase()}.`}
            </p>
          </section>

          <PerguntaADois detalhe={d} conexaoId={conexaoId} aoResponder={carregar} />

          <section className="rounded-3xl border border-borda bg-superficie p-4">
            <p className="rotulo mb-3">O que você já sabe</p>
            <dl className="space-y-2 text-sm">
              {([["Interesses", outra.hobbies.join(", ")], ["Nome", outra.nome], ["Idade", outra.idade && `${outra.idade} anos`],
                ["Onde mora", outra.local], ["Sobre", outra.sobre], ["Igreja", outra.igreja],
                ["Foto", outra.foto ? "Revelada (toque no topo)" : null]] as const).map(([rotulo, valor]) => (
                <div key={rotulo} className="flex gap-3">
                  <dt className="w-24 shrink-0 font-semibold text-texto-2">{rotulo}</dt>
                  <dd className={valor ? "" : "flex items-center gap-1.5 text-texto-2"}>
                    {valor || <><IconeCadeado className="size-3.5" /> ainda em mistério</>}
                  </dd>
                </div>
              ))}
            </dl>
          </section>

          <section className="rounded-3xl border border-borda bg-superficie p-4">
            <p className="rotulo mb-1">O que eu revelo</p>
            <p className="mb-3 text-xs text-texto-2">Seus limites valem para todas as conexões. Aqui dá para liberar antes, só para esta.</p>
            <ul className="space-y-2">
              {d.minhas.map((r) => (
                <li key={r.item} className="flex items-center justify-between gap-3 text-sm">
                  <span className="font-medium">{r.rotulo}</span>
                  {r.revelado ? (
                    <span className="flex items-center gap-1 font-semibold text-sucesso"><IconeCheck className="size-4" /> revelado</span>
                  ) : (
                    <span className="flex items-center gap-2">
                      <span className="text-xs text-texto-2">{r.limite ? `com ${r.limite}` : "só na mão"}</span>
                      <button type="button" onClick={() => setConfirmar({ tipo: "liberar", r })}
                        className="rounded-xl border border-primaria px-2.5 py-1 text-xs font-bold text-primaria hover:bg-primaria/10">
                        Liberar agora
                      </button>
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </section>

          {d.eventos.length > 0 && (
            <section className="rounded-3xl border border-borda bg-superficie p-4">
              <p className="rotulo mb-3">Como vocês chegaram aqui</p>
              <ul className="space-y-2 text-sm">
                {d.eventos.map((e, i) => (
                  <li key={i} className="flex items-center justify-between gap-3">
                    <span className="min-w-0 truncate">{e.titulo}</span>
                    <span className="shrink-0 font-bold text-primaria">+{e.pontos}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </main>
      ) : d.chat_aberto ? (
        <Chat conexaoId={conexaoId} />
      ) : (
        <main className="flex flex-1 flex-col items-center justify-center gap-3 px-8 text-center">
          <IconeCadeado className="size-10 text-destaque" />
          <h2 className="text-xl font-extrabold">O chat ainda está trancado</h2>
          <p className="text-texto-2">
            {d.chat_abre_em ? `Abre com ${d.chat_abre_em} pontos. Faltam ${Math.max(0, d.chat_abre_em - d.pontos)}.`
              : "Abre quando os dois liberarem."} Respondam a pergunta a dois, o devocional e os testes para a afinidade subir.
          </p>
          <Botao onClick={() => setAba("dois")}>Ver a pergunta a dois</Botao>
        </main>
      )}

      {confirmar && (
        <div className="fixed inset-0 z-30 flex items-end justify-center bg-black/60 p-4 sm:items-center" role="dialog"
          aria-modal="true" aria-labelledby="titulo-confirmacao">
          <div className="surgir w-full max-w-md rounded-[28px] bg-superficie p-6">
            <h2 id="titulo-confirmacao" className="text-xl font-extrabold">
              {confirmar.tipo === "liberar" ? `Revelar agora: ${confirmar.r.rotulo.toLowerCase()}?`
                : confirmar.tipo === "desfazer" ? "Encerrar a conexão?" : `Denunciar ${outra.codinome}?`}
            </h2>
            <p className="mt-2 text-texto-2">
              {confirmar.tipo === "liberar" ? "Vale só para esta conexão, e não dá para esconder de novo."
                : confirmar.tipo === "desfazer" ? "A conexão some para os dois e vocês não aparecem mais um para o outro."
                : "A conexão é encerrada e a liderança recebe a denúncia para analisar."}
            </p>
            <div className="mt-6 flex gap-3">
              <Botao variante="secundario" className="flex-1" onClick={() => setConfirmar(null)}>Cancelar</Botao>
              <Botao variante={confirmar.tipo === "liberar" ? "primario" : "perigo"} className="flex-1" onClick={executar}>
                {confirmar.tipo === "liberar" ? "Revelar" : confirmar.tipo === "desfazer" ? "Encerrar" : "Denunciar"}
              </Botao>
            </div>
          </div>
        </div>
      )}

      {verFoto && (
        <button type="button" className="fixed inset-0 z-30 flex items-center justify-center bg-black/85 p-6"
          onClick={() => setVerFoto(false)} aria-label="Fechar foto">
          <Avatar id={outra.id} nome={outra.codinome} liberada tamanho={320} quadrado />
        </button>
      )}
    </div>
  );
}

function PerguntaADois({ detalhe, conexaoId, aoResponder }: {
  detalhe: DetalheDaConexao; conexaoId: number; aoResponder: () => void;
}) {
  const [texto, setTexto] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState("");
  const [ganho, setGanho] = useState<number | null>(null);
  const p = detalhe.pergunta;
  const quem = detalhe.outra.nome || detalhe.outra.codinome;

  async function responder() {
    setErro("");
    setEnviando(true);
    try {
      const r = await api.responderPergunta(conexaoId, texto);
      setTexto("");
      setGanho(r.evento ? r.evento.pontos : null);
      aoResponder();
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Não foi enviada.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <section className="rounded-3xl border border-primaria/40 bg-primaria/5 p-4">
      <p className="rotulo mb-2">Pergunta a dois</p>
      {ganho !== null && (
        <p className="surgir mb-3 flex items-center gap-2 rounded-2xl bg-primaria px-3 py-2 text-sm font-bold text-sobre-primaria">
          <IconeBrilho className="size-4" /> Vocês dois responderam: +{ganho} pontos!
        </p>
      )}
      {p.atual ? (
        <>
          <p className="text-lg leading-snug font-bold">{p.atual.texto}</p>
          {p.atual.minha === null ? (
            <div className="mt-3 space-y-2">
              <textarea value={texto} onChange={(e) => setTexto(e.target.value.slice(0, 1000))} rows={3}
                placeholder="Sua resposta. Você só vê a do outro depois de responder."
                className="w-full resize-none rounded-2xl border border-borda bg-superficie p-3 outline-none focus:border-primaria" />
              {erro && <p role="alert" className="text-sm text-perigo">{erro}</p>}
              <Botao className="w-full" disabled={texto.trim().length < 3 || enviando} onClick={responder}>
                {enviando ? "Enviando…" : "Responder"}
              </Botao>
            </div>
          ) : (
            <Respostas minha={p.atual.minha} dela={p.atual.dela} quem={quem} />
          )}
        </>
      ) : (
        <p className="text-sm text-texto-2">
          {p.volta_amanha ? "Vocês já responderam a pergunta de hoje. Amanhã tem outra!"
            : "Vocês já responderam todas as perguntas. Logo chegam novas."}
        </p>
      )}
      {p.anterior && (
        <div className="mt-4 border-t border-primaria/20 pt-4">
          <p className="mb-1 text-xs font-bold tracking-wide text-texto-2 uppercase">A última de vocês</p>
          <p className="font-semibold">{p.anterior.texto}</p>
          <Respostas minha={p.anterior.minha} dela={p.anterior.dela} quem={quem} />
        </div>
      )}
    </section>
  );
}

function Respostas({ minha, dela, quem }: { minha: string; dela: string | null; quem: string }) {
  return (
    <div className="mt-3 space-y-2 text-sm">
      <div className="rounded-2xl bg-superficie p-3"><p className="mb-1 text-xs font-bold text-texto-2">Você</p>{minha}</div>
      <div className="rounded-2xl bg-superficie p-3">
        <p className="mb-1 text-xs font-bold text-texto-2">{quem}</p>
        {dela ?? <span className="text-texto-2">Ainda não respondeu. Quando responder, vocês ganham pontos.</span>}
      </div>
    </div>
  );
}

function Chat({ conexaoId }: { conexaoId: number }) {
  const [mensagens, setMensagens] = useState<MensagemChat[]>([]);
  const [texto, setTexto] = useState("");
  const [erro, setErro] = useState("");
  const ultimo = useRef(0);
  const fim = useRef<HTMLDivElement>(null);

  const juntar = useCallback((novas: MensagemChat[]) => {
    if (!novas.length) return;
    setMensagens((atuais) => {
      const ids = new Set(atuais.map((m) => m.id));
      return [...atuais, ...novas.filter((m) => !ids.has(m.id))];
    });
    ultimo.current = Math.max(ultimo.current, ...novas.map((m) => m.id));
    api.marcarLido(conexaoId, ultimo.current).catch(() => {});
  }, [conexaoId]);

  useEffect(() => {
    let vivo = true;
    const buscar = () => api.mensagens(conexaoId, ultimo.current).then((r) => vivo && juntar(r.mensagens)).catch(() => {});
    buscar();
    const intervalo = setInterval(buscar, 3000);
    return () => {
      vivo = false;
      clearInterval(intervalo);
    };
  }, [conexaoId, juntar]);

  useEffect(() => {
    fim.current?.scrollIntoView({ block: "end" });
  }, [mensagens.length]);

  async function enviar() {
    const t = texto.trim();
    if (!t) return;
    setTexto("");
    setErro("");
    try {
      juntar([await api.enviar(conexaoId, t)]);
      setTimeout(() => api.mensagens(conexaoId, ultimo.current).then((r) => juntar(r.mensagens)).catch(() => {}), 800);
    } catch (e) {
      setTexto(t);
      setErro(e instanceof Error ? e.message : "Não foi enviada.");
    }
  }

  return (
    <>
      <div className="flex-1 space-y-2 overflow-y-auto px-4 py-4">
        {mensagens.length === 0 && <p className="mt-6 text-center text-sm text-texto-2">O chat abriu! Que tal começar pelo que vocês responderam parecido?</p>}
        {mensagens.map((m) => (
          <div key={m.id} className={`flex ${m.minha ? "justify-end" : "justify-start"}`}>
            <p className={`max-w-[80%] rounded-3xl px-4 py-2.5 break-words whitespace-pre-wrap ${
              m.minha ? "rounded-br-lg bg-primaria text-sobre-primaria" : "rounded-bl-lg border border-borda bg-superficie"}`}>
              {m.texto}
              <span className={`mt-0.5 block text-right text-[10px] ${m.minha ? "text-white/70" : "text-texto-2"}`}>
                {new Date(m.criado_em).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}
              </span>
            </p>
          </div>
        ))}
        <div ref={fim} />
      </div>
      <form className="pb-seguro flex items-end gap-2 border-t border-borda bg-superficie px-3 pt-2"
        onSubmit={(e) => { e.preventDefault(); enviar(); }}>
        <div className="flex-1">
          {erro && <p role="alert" className="mb-1 text-xs text-perigo">{erro}</p>}
          <textarea value={texto} onChange={(e) => setTexto(e.target.value)} rows={1} maxLength={1000}
            placeholder="Escreva uma mensagem" aria-label="Mensagem"
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); enviar(); } }}
            className="max-h-32 min-h-11 w-full resize-none rounded-3xl border border-borda bg-fundo px-4 py-2.5 outline-none focus:border-primaria" />
        </div>
        <button type="submit" disabled={!texto.trim()} aria-label="Enviar"
          className="mb-0.5 flex size-11 shrink-0 items-center justify-center rounded-full bg-primaria text-sobre-primaria disabled:opacity-40">
          <IconeEnviar className="size-5" />
        </button>
      </form>
    </>
  );
}
