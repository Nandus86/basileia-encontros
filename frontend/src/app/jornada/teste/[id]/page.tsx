"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Botao, Protegida } from "@/components/estrutura";
import { IconeBrilho, IconeVoltar } from "@/components/icones";
import { useSessao } from "@/contexts/sessao";
import { api } from "@/lib/api";
import type { Teste } from "@/types";

export default function FazerTeste() {
  return (
    <Protegida completo={false}>
      <Perguntas />
    </Protegida>
  );
}

function Perguntas() {
  const { id } = useParams<{ id: string }>();
  const { perfil, atualizar } = useSessao();
  const [teste, setTeste] = useState<Teste | null>(null);
  const [escolhas, setEscolhas] = useState<number[]>([]);
  const [atual, setAtual] = useState(0);
  const [erro, setErro] = useState("");
  const [ganho, setGanho] = useState<number | null>(null);

  useEffect(() => {
    api.teste(Number(id)).then(setTeste).catch((e) => setErro(e.message));
  }, [id]);

  async function escolher(opcao: number) {
    if (!teste) return;
    const novas = [...escolhas.slice(0, atual), opcao];
    setEscolhas(novas);
    if (atual < teste.lista.length - 1) return setAtual(atual + 1);
    try {
      const r = await api.fazerTeste(teste.id, novas);
      setGanho(r.ganhou);
      if (perfil) atualizar({ ...perfil, jornada: r.pontos });
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Não foi salvo.");
    }
  }

  return (
    <div className="mx-auto flex min-h-dvh max-w-md flex-col px-5 pt-[max(env(safe-area-inset-top),1rem)] pb-8">
      <Link href="/jornada" className="mb-4 flex items-center gap-1 text-sm font-semibold text-texto-2"><IconeVoltar className="size-5" /> Jornada</Link>
      {erro && <p role="alert" className="rounded-xl bg-perigo/10 px-4 py-3 text-sm text-perigo">{erro}</p>}
      {teste && ganho === null && teste.feito && <p className="text-texto-2">Você já fez este teste.</p>}
      {teste && ganho === null && !teste.feito && (
        <>
          <p className="rotulo">{teste.titulo}</p>
          <div className="mt-3 flex gap-1.5" aria-hidden="true">
            {teste.lista.map((_, i) => <span key={i} className={`h-1.5 flex-1 rounded-full ${i <= atual ? "bg-primaria" : "bg-borda"}`} />)}
          </div>
          <main key={atual} className="surgir flex-1 py-8">
            <p className="text-sm font-semibold text-texto-2">{atual + 1} de {teste.lista.length}</p>
            <h1 className="mt-1 text-2xl font-extrabold">{teste.lista[atual].texto}</h1>
            <div className="mt-6 space-y-2">
              {teste.lista[atual].opcoes.map((o, i) => (
                <button key={o} type="button" onClick={() => escolher(i)}
                  className={`block w-full rounded-2xl border p-4 text-left font-medium transition hover:border-primaria ${
                    escolhas[atual] === i ? "border-primaria bg-primaria/10" : "border-borda bg-superficie"}`}>
                  {o}
                </button>
              ))}
            </div>
            <p className="mt-6 text-xs text-texto-2">Não existe resposta certa. Responda como você vive hoje.</p>
          </main>
          {atual > 0 && <Botao variante="fantasma" onClick={() => setAtual(atual - 1)}>Voltar uma</Botao>}
        </>
      )}
      {ganho !== null && (
        <div className="surgir flex flex-1 flex-col items-center justify-center gap-3 text-center">
          <IconeBrilho className="size-12 text-primaria" />
          <h1 className="text-3xl font-extrabold">+{ganho} pontos!</h1>
          <p className="text-texto-2">
            A IA agora conhece um pouco mais de você. Se alguma conexão sua fizer este teste, a afinidade de vocês sobe
            conforme as respostas se parecerem.
          </p>
          <Link href="/jornada" className="mt-3"><Botao>Voltar para a jornada</Botao></Link>
        </div>
      )}
    </div>
  );
}
