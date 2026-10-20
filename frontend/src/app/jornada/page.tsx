"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Botao, Protegida, Tela } from "@/components/estrutura";
import { IconeBrilho, IconeCheck, IconeFogo, IconeLivro } from "@/components/icones";
import { useSessao } from "@/contexts/sessao";
import { api } from "@/lib/api";
import type { Devocional, Jornada as TipoJornada, ResumoDoTeste } from "@/types";

const SIMBOLO_DO_NIVEL: Record<string, string> = { Semente: "🌱", Broto: "🌿", Raiz: "🪴", Árvore: "🌳", Fruto: "🍇" };

export default function Jornada() {
  return (
    <Protegida completo={false}>
      <Tela titulo="Jornada">
        <Conteudo />
      </Tela>
    </Protegida>
  );
}

type Dados = TipoJornada & { devocional: Devocional | null; testes: ResumoDoTeste[] };

function Conteudo() {
  const [dados, setDados] = useState<Dados | null>(null);
  const [erro, setErro] = useState("");

  useEffect(() => {
    api.jornada().then(setDados).catch((e) => setErro(e.message));
  }, []);

  if (erro && !dados) return <p role="alert" className="mt-6 text-center text-perigo">{erro}</p>;
  if (!dados) return <div className="mt-10 flex justify-center"><div className="size-8 animate-spin rounded-full border-4 border-borda border-t-primaria" /></div>;

  const faixa = dados.proximo_em ? (dados.pontos - dados.nivel_desde) / (dados.proximo_em - dados.nivel_desde) : 1;
  return (
    <div className="space-y-4 pb-6">
      <section className="rounded-3xl bg-gradient-to-br from-primaria to-primaria-forte p-5 text-sobre-primaria shadow-cartao">
        <div className="flex items-center gap-4">
          <span className="flex size-16 items-center justify-center rounded-2xl bg-white/15 text-4xl" aria-hidden="true">
            {SIMBOLO_DO_NIVEL[dados.nivel] ?? "🌱"}
          </span>
          <div>
            <p className="text-sm font-semibold text-white/80">Seu nível</p>
            <p className="text-3xl font-black">{dados.nivel}</p>
            <p className="text-sm text-white/80">{dados.pontos} pontos de jornada</p>
          </div>
        </div>
        <div className="mt-4 h-2.5 rounded-full bg-white/20">
          <div className="h-full rounded-full bg-white" style={{ width: `${Math.max(4, faixa * 100)}%` }} />
        </div>
        <p className="mt-1.5 text-xs text-white/80">
          {dados.proximo_nivel ? `${dados.proximo_em! - dados.pontos} pontos para ${dados.proximo_nivel}` : "Você chegou ao último nível!"}
          {" · "}{dados.sinais_por_dia} sinais por dia
        </p>
        <div className="mt-4 grid grid-cols-2 gap-2 text-center">
          <div className="rounded-2xl bg-white/10 p-3">
            <p className="flex items-center justify-center gap-1 text-2xl font-black"><IconeFogo className="size-5" />{dados.sequencia}</p>
            <p className="text-xs text-white/80">dias seguidos</p>
          </div>
          <div className="rounded-2xl bg-white/10 p-3">
            <p className="text-2xl font-black">{dados.profundidade}%</p>
            <p className="text-xs text-white/80">o quanto a IA conhece você</p>
          </div>
        </div>
      </section>

      {dados.devocional ? (
        <DevocionalDoDia devocional={dados.devocional} aoConcluir={(j) => setDados({ ...dados, ...j })} />
      ) : (
        <p className="rounded-3xl border border-borda bg-superficie p-4 text-sm text-texto-2">
          O devocional de hoje ainda não foi publicado pela liderança.
        </p>
      )}

      <section>
        <p className="rotulo mb-3">Testes de visão e vivência</p>
        <p className="mb-3 text-sm text-texto-2">
          Não têm resposta certa: mostram como você vive a fé. Quando alguém com quem você tem conexão faz o mesmo
          teste, a afinidade de vocês sobe conforme as respostas se parecem.
        </p>
        <ul className="space-y-2">
          {dados.testes.map((t) => (
            <li key={t.id}>
              <Link href={t.feito ? "#" : `/jornada/teste/${t.id}`} aria-disabled={t.feito}
                className={`flex items-center gap-3 rounded-2xl border border-borda bg-superficie p-4 ${t.feito ? "opacity-70" : "hover:border-primaria"}`}>
                <IconeLivro className="size-6 shrink-0 text-primaria" />
                <div className="min-w-0 flex-1">
                  <p className="font-bold">{t.titulo}</p>
                  <p className="text-xs text-texto-2">{t.questoes} perguntas · {t.tema}</p>
                </div>
                {t.feito ? <span className="flex items-center gap-1 text-sm font-semibold text-sucesso"><IconeCheck className="size-4" /> feito</span>
                  : <span className="text-sm font-bold text-primaria">+40</span>}
              </Link>
            </li>
          ))}
          {dados.testes.length === 0 && <li className="text-sm text-texto-2">Nenhum teste publicado ainda.</li>}
        </ul>
      </section>
    </div>
  );
}

function DevocionalDoDia({ devocional, aoConcluir }: { devocional: Devocional; aoConcluir: (j: TipoJornada) => void }) {
  const { perfil, atualizar } = useSessao();
  const [texto, setTexto] = useState("");
  const [minha, setMinha] = useState(devocional.minha);
  const [ganho, setGanho] = useState<number | null>(null);
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function concluir() {
    setErro("");
    setEnviando(true);
    try {
      const r = await api.fazerDevocional(texto);
      setMinha(texto);
      setGanho(r.ganhou);
      aoConcluir(r);
      if (perfil) atualizar({ ...perfil, jornada: r.pontos });
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Não foi salvo.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <section className="rounded-3xl border border-borda bg-superficie p-5">
      <p className="rotulo mb-2">Devocional de hoje</p>
      <h2 className="text-xl font-extrabold">{devocional.titulo}</h2>
      <p className="mt-1 text-sm font-semibold text-primaria">Leia na sua Bíblia: {devocional.referencia}</p>
      <p className="mt-3 leading-relaxed">{devocional.reflexao}</p>
      <div className="mt-4 rounded-2xl bg-superficie-2 p-4">
        <p className="font-bold">{devocional.pergunta}</p>
        {minha ? (
          <>
            <p className="mt-2 text-sm text-texto-2">{minha}</p>
            <p className="mt-3 flex items-center gap-2 text-sm font-bold text-sucesso">
              <IconeCheck className="size-4" /> Feito hoje{ganho ? ` · +${ganho} pontos` : ""}
            </p>
          </>
        ) : (
          <div className="mt-3 space-y-2">
            <textarea value={texto} onChange={(e) => setTexto(e.target.value.slice(0, 1000))} rows={3}
              placeholder="Escreva em uma ou duas frases" aria-label="Sua resposta ao devocional"
              className="w-full resize-none rounded-2xl border border-borda bg-superficie p-3 outline-none focus:border-primaria" />
            {erro && <p role="alert" className="text-sm text-perigo">{erro}</p>}
            <Botao className="w-full" disabled={texto.trim().length < 3 || enviando} onClick={concluir}>
              <IconeBrilho className="size-5" /> {enviando ? "Salvando…" : "Concluir devocional"}
            </Botao>
          </div>
        )}
      </div>
    </section>
  );
}
