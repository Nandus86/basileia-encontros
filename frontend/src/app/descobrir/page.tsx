"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Avatar } from "@/components/avatar";
import { CartaoPessoa } from "@/components/cartao-pessoa";
import { Botao, Logo, Protegida, Tela } from "@/components/estrutura";
import { IconeBrilho, IconeCoracao, IconeX } from "@/components/icones";
import { useSessao } from "@/contexts/sessao";
import { api } from "@/lib/api";
import type { Cartao } from "@/types";

export default function Descobrir() {
  return (
    <Protegida>
      <Tela titulo={<Logo pequeno />}>
        <Baralho />
      </Tela>
    </Protegida>
  );
}

function Baralho() {
  const { perfil } = useSessao();
  const [cartoes, setCartoes] = useState<Cartao[] | null>(null);
  const [erro, setErro] = useState("");
  const [match, setMatch] = useState<{ id: number; pessoa: Cartao } | null>(null);
  const [ocupado, setOcupado] = useState(false);

  const buscar = useCallback(() => {
    api.descobrir().then((r) => setCartoes(r.cartoes)).catch((e) => {
      setErro(e.message);
      setCartoes([]);
    });
  }, []);

  useEffect(buscar, [buscar]);

  function procurarDeNovo() {
    setErro("");
    setCartoes(null);
    buscar();
  }

  async function decidir(curtiu: boolean) {
    const atual = cartoes?.[0];
    if (!atual || ocupado) return;
    setOcupado(true);
    setCartoes((c) => c?.slice(1) ?? null);
    try {
      const r = await api.reagir(atual.id, curtiu);
      if (r.match) setMatch(r.match);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Não consegui registrar.");
    } finally {
      setOcupado(false);
    }
  }

  if (perfil && !perfil.visivel) {
    return (
      <Vazio titulo="Seu perfil está pausado" texto="Enquanto estiver pausado, você não aparece nem vê ninguém novo.">
        <Link href="/perfil"><Botao>Ir para o perfil</Botao></Link>
      </Vazio>
    );
  }

  if (cartoes === null) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4 text-center" role="status">
        <IconeBrilho className="size-10 animate-pulse text-primaria" />
        <p className="font-semibold">Procurando quem combina com você…</p>
        <p className="text-sm text-texto-2">A IA está comparando hobbies e distância.</p>
      </div>
    );
  }

  const atual = cartoes[0];
  return (
    <>
      {erro && <p role="alert" className="mb-3 rounded-xl bg-perigo/10 px-4 py-3 text-sm font-medium text-perigo">{erro}</p>}
      {atual ? (
        <div className="flex flex-1 flex-col">
          <div className="relative min-h-[460px] flex-1">
            {cartoes[1] && (
              <div className="absolute inset-x-3 top-3 bottom-0 rounded-[28px] border border-borda bg-superficie-2" aria-hidden="true" />
            )}
            <CartaoPessoa key={atual.id} cartao={atual} aoDecidir={decidir} />
          </div>
          <div className="flex items-center justify-center gap-8 py-5">
            <button type="button" onClick={() => decidir(false)} disabled={ocupado} aria-label={`Passar ${atual.nome}`}
              className="flex size-16 items-center justify-center rounded-full border border-borda bg-superficie text-texto-2 shadow-cartao transition hover:scale-105 active:scale-95">
              <IconeX className="size-8" />
            </button>
            <button type="button" onClick={() => decidir(true)} disabled={ocupado} aria-label={`Curtir ${atual.nome}`}
              className="flex size-20 items-center justify-center rounded-full bg-primaria text-sobre-primaria shadow-cartao transition hover:scale-105 active:scale-95">
              <IconeCoracao className="size-9" />
            </button>
          </div>
        </div>
      ) : (
        <Vazio titulo="Por hoje é só"
          texto="Você já viu todo mundo que combina com você agora. Volte depois: sempre chega gente nova. Mais hobbies ou uma distância maior também ajudam.">
          <div className="flex gap-3">
            <Botao variante="secundario" onClick={procurarDeNovo}>Procurar de novo</Botao>
            <Link href="/perfil"><Botao>Ajustar perfil</Botao></Link>
          </div>
        </Vazio>
      )}

      {match && <DeuMatch match={match} fechar={() => setMatch(null)} />}
    </>
  );
}

function Vazio({ titulo, texto, children }: { titulo: string; texto: string; children?: React.ReactNode }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 px-4 text-center">
      <IconeBrilho className="size-10 text-destaque" />
      <h2 className="text-xl font-extrabold">{titulo}</h2>
      <p className="text-texto-2">{texto}</p>
      <div className="mt-3">{children}</div>
    </div>
  );
}

function DeuMatch({ match, fechar }: { match: { id: number; pessoa: Cartao }; fechar: () => void }) {
  const { perfil } = useSessao();
  return (
    <div className="fixed inset-0 z-30 flex items-end justify-center bg-black/60 p-4 backdrop-blur-sm sm:items-center"
      role="dialog" aria-modal="true" aria-labelledby="titulo-match">
      <div className="surgir w-full max-w-md rounded-[28px] bg-superficie p-6 text-center">
        <div className="flex justify-center -space-x-4">
          {perfil && <Avatar id={perfil.id} nome={perfil.nome_publico} liberada tamanho={88} />}
          <Avatar id={match.pessoa.id} nome={match.pessoa.nome} liberada={false} tamanho={88} />
        </div>
        <h2 id="titulo-match" className="mt-5 text-3xl font-extrabold text-primaria">Deu match!</h2>
        <p className="mt-2 text-texto-2">
          Você e {match.pessoa.nome} se curtiram. As fotos aparecem quando cada um liberar a sua na conversa.
        </p>
        <div className="mt-6 space-y-2">
          <Link href={`/conversas/${match.id}`} className="block"><Botao className="w-full">Mandar uma mensagem</Botao></Link>
          <Botao variante="fantasma" className="w-full" onClick={fechar}>Continuar descobrindo</Botao>
        </div>
      </div>
    </div>
  );
}
