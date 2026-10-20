"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { tom } from "@/components/avatar";
import { Botao, Logo, Protegida, Tela } from "@/components/estrutura";
import { IconeBrilho, IconeCadeado } from "@/components/icones";
import { api } from "@/lib/api";
import type { Publico, Sinal } from "@/types";

export default function Sinais() {
  return (
    <Protegida>
      <Tela titulo={<Logo pequeno />}>
        <SinaisDoDia />
      </Tela>
    </Protegida>
  );
}

function SinaisDoDia() {
  const [sinais, setSinais] = useState<Sinal[] | null>(null);
  const [demo, setDemo] = useState(false);
  const [erro, setErro] = useState("");
  const [ocupado, setOcupado] = useState<number | null>(null);
  const [conexao, setConexao] = useState<{ id: number; pontos: number; outra: Publico } | null>(null);

  const buscar = useCallback(() => {
    api.sinais().then((r) => {
      setSinais(r.sinais);
      setDemo(r.demo);
    }).catch((e) => {
      setErro(e.message);
      setSinais([]);
    });
  }, []);

  useEffect(buscar, [buscar]);

  async function responder(s: Sinal, enviar: boolean) {
    setOcupado(s.id);
    setErro("");
    try {
      const r = await api.responderSinal(s.id, enviar);
      setSinais((lista) => lista?.filter((x) => x.id !== s.id) ?? null);
      if (r.conexao) setConexao(r.conexao);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Não deu certo.");
    } finally {
      setOcupado(null);
    }
  }

  async function maisSinais() {
    setSinais(null);
    await api.maisSinais().catch(() => {});
    buscar();
  }

  if (sinais === null) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4 text-center" role="status">
        <IconeBrilho className="size-10 animate-pulse text-primaria" />
        <p className="font-semibold">Procurando sinais para você…</p>
        <p className="text-sm text-texto-2">A IA compara interesses, valores e o que você tem respondido.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4 pb-4">
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight">Sinais de hoje</h1>
        <p className="text-sm text-texto-2">
          Poucas pessoas por dia, escolhidas pela afinidade. Ninguém sabe quem é quem: só os interesses.
        </p>
      </div>
      {erro && <p role="alert" className="rounded-xl bg-perigo/10 px-4 py-3 text-sm font-medium text-perigo">{erro}</p>}

      {sinais.map((s) => (
        <article key={s.id} className="surgir overflow-hidden rounded-[28px] border border-borda bg-superficie shadow-cartao">
          <div className="relative flex items-center gap-4 p-5 text-white" style={{ background: tom(s.id) }}>
            <span className="flex size-16 shrink-0 items-center justify-center rounded-2xl bg-white/15 text-4xl" aria-hidden="true">
              {s.simbolo}
            </span>
            <div className="min-w-0">
              <h2 className="truncate text-2xl font-extrabold">{s.codinome}</h2>
              <p className="flex items-center gap-1.5 text-xs text-white/80">
                <IconeCadeado className="size-3.5" /> Nome, idade e foto revelados aos poucos
              </p>
            </div>
          </div>
          <div className="space-y-4 p-5">
            <ul className="space-y-1.5">
              {s.motivos.map((m) => (
                <li key={m} className="flex gap-2 text-sm font-medium">
                  <IconeBrilho className="mt-0.5 size-4 shrink-0 text-primaria" /> {m}
                </li>
              ))}
            </ul>
            <div className="flex flex-wrap gap-2">
              {s.hobbies.map((h) => (
                <span key={h} className={`rounded-full px-3 py-1.5 text-sm ${s.em_comum.includes(h)
                  ? "bg-primaria font-semibold text-sobre-primaria" : "border border-borda"}`}>{h}</span>
              ))}
            </div>
            <div className="flex gap-3">
              <Botao variante="secundario" className="flex-1" disabled={ocupado === s.id} onClick={() => responder(s, false)}>
                Agora não
              </Botao>
              <Botao className="flex-1" disabled={ocupado === s.id} onClick={() => responder(s, true)}>
                <IconeBrilho className="size-5" /> Enviar sinal
              </Botao>
            </div>
          </div>
        </article>
      ))}

      {sinais.length === 0 && (
        <div className="flex flex-col items-center gap-3 px-4 py-12 text-center">
          <IconeBrilho className="size-10 text-destaque" />
          <h2 className="text-xl font-extrabold">Por hoje é só</h2>
          <p className="text-texto-2">
            Amanhã chegam novos sinais. Enquanto isso, faça o devocional: quanto mais você responde, mais a IA entende
            quem combina com você, e no nível Raiz você recebe mais sinais por dia.
          </p>
          <div className="mt-2 flex flex-wrap justify-center gap-3">
            <Link href="/jornada"><Botao>Ir para a jornada</Botao></Link>
            {demo && <Botao variante="secundario" onClick={maisSinais}>Mais sinais (modo de teste)</Botao>}
          </div>
        </div>
      )}

      {conexao && (
        <div className="fixed inset-0 z-30 flex items-end justify-center bg-black/60 p-4 backdrop-blur-sm sm:items-center"
          role="dialog" aria-modal="true" aria-labelledby="titulo-conexao">
          <div className="surgir w-full max-w-md rounded-[28px] bg-superficie p-6 text-center">
            <div className="mx-auto flex size-20 items-center justify-center rounded-3xl text-5xl" style={{ background: tom(conexao.outra.id) }}>
              {conexao.outra.simbolo}
            </div>
            <h2 id="titulo-conexao" className="mt-4 text-3xl font-extrabold text-primaria">Conexão!</h2>
            <p className="mt-2 text-texto-2">
              Você e {conexao.outra.codinome} enviaram sinal um para o outro. Vocês começam com{" "}
              <strong className="text-texto">{conexao.pontos} pontos</strong> de afinidade. Respondam a pergunta a dois
              para descobrir mais.
            </p>
            <div className="mt-6 space-y-2">
              <Link href={`/conexoes/${conexao.id}`} className="block"><Botao className="w-full">Ver a conexão</Botao></Link>
              <Botao variante="fantasma" className="w-full" onClick={() => setConexao(null)}>Continuar</Botao>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
