"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { Avatar } from "@/components/avatar";
import { Botao, Protegida } from "@/components/estrutura";
import { IconeCadeado, IconeEnviar, IconeMais, IconeVoltar } from "@/components/icones";
import { api, ErroDaApi } from "@/lib/api";
import type { Cartao, MensagemChat } from "@/types";

const INTERVALO = 3000;

export default function Conversa() {
  return (
    <Protegida>
      <Bate />
    </Protegida>
  );
}

type Estado = { pessoa: Cartao; foto_liberada: boolean; eu_liberei: boolean };

function Bate() {
  const { id } = useParams<{ id: string }>();
  const matchId = Number(id);
  const router = useRouter();
  const [estado, setEstado] = useState<Estado | null>(null);
  const [mensagens, setMensagens] = useState<MensagemChat[]>([]);
  const [texto, setTexto] = useState("");
  const [erro, setErro] = useState("");
  const [menu, setMenu] = useState(false);
  const [confirmar, setConfirmar] = useState<null | "foto" | "desfazer" | "denunciar">(null);
  const [verFoto, setVerFoto] = useState(false);
  const ultimo = useRef(0);
  const fim = useRef<HTMLDivElement>(null);

  const juntar = useCallback((novas: MensagemChat[]) => {
    if (!novas.length) return;
    setMensagens((atuais) => {
      const ids = new Set(atuais.map((m) => m.id));
      return [...atuais, ...novas.filter((m) => !ids.has(m.id))];
    });
    ultimo.current = Math.max(ultimo.current, ...novas.map((m) => m.id));
    api.marcarLido(matchId, ultimo.current).catch(() => {});
  }, [matchId]);

  useEffect(() => {
    let vivo = true;
    api.match(matchId)
      .then((m) => vivo && setEstado({ pessoa: m.pessoa, foto_liberada: m.foto_liberada, eu_liberei: m.eu_liberei }))
      .catch((e) => e instanceof ErroDaApi && e.status === 404 && router.replace("/conversas"));
    const buscar = () =>
      api.mensagens(matchId, ultimo.current).then((r) => {
        if (!vivo) return;
        juntar(r.mensagens);
        setEstado((s) => (s ? { ...s, foto_liberada: r.foto_liberada, eu_liberei: r.eu_liberei } : s));
      }).catch(() => {});
    buscar();
    const intervalo = setInterval(buscar, INTERVALO);
    return () => {
      vivo = false;
      clearInterval(intervalo);
    };
  }, [matchId, juntar, router]);

  useEffect(() => {
    fim.current?.scrollIntoView({ block: "end" });
  }, [mensagens.length]);

  async function enviar() {
    const t = texto.trim();
    if (!t) return;
    setTexto("");
    setErro("");
    try {
      juntar([await api.enviar(matchId, t)]);
    } catch (e) {
      setTexto(t);
      setErro(e instanceof Error ? e.message : "Não foi enviada.");
    }
  }

  async function executar() {
    if (!estado) return;
    try {
      if (confirmar === "foto") {
        await api.liberarFoto(matchId);
        setEstado({ ...estado, eu_liberei: true });
      } else if (confirmar === "desfazer") {
        await api.desfazer(matchId);
        router.replace("/conversas");
      } else if (confirmar === "denunciar") {
        await api.denunciar(estado.pessoa.id, "Denúncia pela conversa");
        router.replace("/conversas");
      }
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Não deu certo.");
    }
    setConfirmar(null);
  }

  if (!estado) return <div className="flex min-h-dvh items-center justify-center"><div className="size-8 animate-spin rounded-full border-4 border-borda border-t-primaria" /></div>;
  const { pessoa } = estado;

  return (
    <div className="mx-auto flex h-dvh max-w-md flex-col">
      <header className="flex items-center gap-2 border-b border-borda bg-superficie px-2 pt-[max(env(safe-area-inset-top),0.5rem)] pb-2">
        <Link href="/conversas" aria-label="Voltar" className="rounded-full p-2 hover:bg-superficie-2"><IconeVoltar /></Link>
        <button type="button" className="flex min-w-0 flex-1 items-center gap-3 text-left" disabled={!estado.foto_liberada}
          onClick={() => setVerFoto(true)} aria-label={estado.foto_liberada ? `Ver a foto de ${pessoa.nome}` : undefined}>
          <Avatar id={pessoa.id} nome={pessoa.nome} liberada={estado.foto_liberada} tamanho={42} />
          <div className="min-w-0">
            <p className="truncate font-bold">{pessoa.nome}, {pessoa.idade}</p>
            <p className="truncate text-xs text-texto-2">
              {estado.foto_liberada ? "Liberou a foto para você" : `${pessoa.cidade}${pessoa.em_comum.length ? ` · ${pessoa.em_comum.slice(0, 2).join(", ")}` : ""}`}
            </p>
          </div>
        </button>
        <div className="relative">
          <button type="button" onClick={() => setMenu(!menu)} aria-label="Mais opções" aria-expanded={menu}
            className="rounded-full p-2 hover:bg-superficie-2"><IconeMais /></button>
          {menu && (
            <div className="surgir absolute right-0 z-10 mt-1 w-52 overflow-hidden rounded-2xl border border-borda bg-superficie shadow-cartao">
              <button type="button" className="block w-full px-4 py-3 text-left hover:bg-superficie-2"
                onClick={() => { setMenu(false); setConfirmar("desfazer"); }}>Desfazer match</button>
              <button type="button" className="block w-full px-4 py-3 text-left text-perigo hover:bg-superficie-2"
                onClick={() => { setMenu(false); setConfirmar("denunciar"); }}>Denunciar</button>
            </div>
          )}
        </div>
      </header>

      {!estado.eu_liberei && (
        <div className="flex items-center gap-3 border-b border-borda bg-superficie-2 px-4 py-3">
          <IconeCadeado className="size-5 shrink-0 text-primaria" />
          <p className="flex-1 text-sm">Sua foto está escondida para {pessoa.nome}.</p>
          <Botao className="min-h-9 rounded-xl px-3 text-sm" onClick={() => setConfirmar("foto")}>Liberar</Botao>
        </div>
      )}

      <div className="flex-1 space-y-2 overflow-y-auto px-4 py-4">
        {mensagens.length === 0 && (
          <div className="mx-auto mt-6 max-w-xs text-center text-sm text-texto-2">
            <p className="font-semibold text-texto">Vocês deram match!</p>
            {pessoa.em_comum.length > 0 && <p className="mt-1">Vocês dois curtem {pessoa.em_comum.join(", ")}. Que tal começar por aí?</p>}
          </div>
        )}
        {mensagens.map((m) => (
          <div key={m.id} className={`flex ${m.minha ? "justify-end" : "justify-start"}`}>
            <p className={`max-w-[80%] rounded-3xl px-4 py-2.5 break-words whitespace-pre-wrap ${
              m.minha ? "rounded-br-lg bg-primaria text-sobre-primaria" : "rounded-bl-lg border border-borda bg-superficie"
            }`}>
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

      {confirmar && (
        <Confirmacao
          titulo={{ foto: "Liberar sua foto?", desfazer: "Desfazer o match?", denunciar: `Denunciar ${pessoa.nome}?` }[confirmar]}
          texto={{
            foto: `${pessoa.nome} vai poder ver a sua foto nesta conversa. Depois de liberada, não dá para esconder de novo.`,
            desfazer: "A conversa some para os dois e vocês não aparecem mais um para o outro.",
            denunciar: "A conversa é encerrada e a liderança da igreja recebe a denúncia para analisar.",
          }[confirmar]}
          botao={{ foto: "Liberar foto", desfazer: "Desfazer", denunciar: "Denunciar" }[confirmar]}
          perigo={confirmar !== "foto"}
          aoConfirmar={executar}
          aoCancelar={() => setConfirmar(null)}
        />
      )}

      {verFoto && (
        <button type="button" className="fixed inset-0 z-30 flex items-center justify-center bg-black/85 p-6"
          onClick={() => setVerFoto(false)} aria-label="Fechar foto">
          <Avatar id={pessoa.id} nome={pessoa.nome} liberada tamanho={320} quadrado />
        </button>
      )}
    </div>
  );
}

function Confirmacao({ titulo, texto, botao, perigo, aoConfirmar, aoCancelar }: {
  titulo: string; texto: string; botao: string; perigo: boolean; aoConfirmar: () => void; aoCancelar: () => void;
}) {
  return (
    <div className="fixed inset-0 z-30 flex items-end justify-center bg-black/60 p-4 sm:items-center" role="dialog"
      aria-modal="true" aria-labelledby="titulo-confirmacao">
      <div className="surgir w-full max-w-md rounded-[28px] bg-superficie p-6">
        <h2 id="titulo-confirmacao" className="text-xl font-extrabold">{titulo}</h2>
        <p className="mt-2 text-texto-2">{texto}</p>
        <div className="mt-6 flex gap-3">
          <Botao variante="secundario" className="flex-1" onClick={aoCancelar}>Cancelar</Botao>
          <Botao variante={perigo ? "perigo" : "primario"} className="flex-1" onClick={aoConfirmar}>{botao}</Botao>
        </div>
      </div>
    </div>
  );
}
