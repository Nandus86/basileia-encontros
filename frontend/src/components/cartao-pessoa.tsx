"use client";

import { useRef, useState } from "react";
import type { Cartao } from "@/types";
import { tom } from "./avatar";
import { IconeBrilho, IconeCadeado, IconeIgreja, IconeLocal } from "./icones";

const NIVEL = { alta: "Muita afinidade", media: "Boa afinidade", baixa: "Pouca afinidade" };
const LIMITE = 110;

/** Cartão sem foto: a inicial num degradê, a afinidade e os hobbies em comum em destaque.
 *  Arrastar para os lados decide (direita curte, esquerda passa); os botões fazem o mesmo. */
export function CartaoPessoa({ cartao, aoDecidir }: { cartao: Cartao; aoDecidir: (curtiu: boolean) => void }) {
  const [dx, setDx] = useState(0);
  const [saindo, setSaindo] = useState<null | boolean>(null);
  const [arrastando, setArrastando] = useState(false);
  const inicio = useRef<number | null>(null);

  function soltar() {
    if (inicio.current === null) return;
    inicio.current = null;
    setArrastando(false);
    if (Math.abs(dx) > LIMITE) {
      setSaindo(dx > 0);
      setTimeout(() => aoDecidir(dx > 0), 180);
    } else setDx(0);
  }

  const deslocamento = saindo === null ? dx : saindo ? 600 : -600;
  const comuns = new Set(cartao.em_comum);
  return (
    <article
      className="absolute inset-0 flex touch-pan-y flex-col overflow-hidden rounded-[28px] border border-borda bg-superficie shadow-cartao select-none"
      style={{
        transform: `translateX(${deslocamento}px) rotate(${deslocamento / 22}deg)`,
        transition: arrastando ? "none" : "transform 200ms ease-out",
      }}
      onPointerDown={(e) => { inicio.current = e.clientX; setArrastando(true); e.currentTarget.setPointerCapture?.(e.pointerId); }}
      onPointerMove={(e) => inicio.current !== null && setDx(e.clientX - inicio.current)}
      onPointerUp={soltar}
      onPointerCancel={soltar}
      aria-label={`${cartao.nome}, ${cartao.idade} anos`}
    >
      <div className="relative flex h-[34%] min-h-40 shrink-0 items-center justify-center text-white" style={{ background: tom(cartao.id) }}>
        <span className="text-8xl font-black opacity-90">{cartao.nome.charAt(0)}</span>
        <span className="absolute bottom-3 left-3 flex items-center gap-1.5 rounded-full bg-black/35 px-3 py-1.5 text-xs font-medium backdrop-blur">
          <IconeCadeado className="size-3.5" /> Foto liberada só na conversa
        </span>
        {cartao.afinidade && (
          <span className="absolute top-3 right-3 flex items-center gap-1.5 rounded-full bg-white/90 px-3 py-1.5 text-xs font-bold text-[#4c1d95]">
            <IconeBrilho className="size-3.5" /> {NIVEL[cartao.afinidade.nivel]}
          </span>
        )}
        {dx > 40 && <span className="absolute top-5 left-5 rotate-[-12deg] rounded-xl border-4 border-white px-3 py-1 text-2xl font-black">CURTIR</span>}
        {dx < -40 && <span className="absolute top-5 right-5 rotate-12 rounded-xl border-4 border-white px-3 py-1 text-2xl font-black">PASSAR</span>}
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto p-5">
        <div>
          <h2 className="text-3xl font-extrabold tracking-tight">
            {cartao.nome}<span className="font-semibold text-texto-2">, {cartao.idade}</span>
          </h2>
          <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-sm text-texto-2">
            <span className="flex items-center gap-1"><IconeLocal className="size-4" />
              {cartao.cidade}{cartao.distancia_km ? ` · a ~${cartao.distancia_km} km` : ""}</span>
            <span className="flex items-center gap-1"><IconeIgreja className="size-4" />{cartao.igreja}</span>
          </div>
        </div>

        {cartao.em_comum.length > 0 && (
          <div>
            <p className="rotulo mb-2">Em comum</p>
            <div className="flex flex-wrap gap-2">
              {cartao.em_comum.map((h) => (
                <span key={h} className="rounded-full bg-primaria px-3 py-1.5 text-sm font-semibold text-sobre-primaria">{h}</span>
              ))}
            </div>
          </div>
        )}
        {cartao.hobbies.some((h) => !comuns.has(h)) && (
          <div>
            <p className="rotulo mb-2">Também curte</p>
            <div className="flex flex-wrap gap-2">
              {cartao.hobbies.filter((h) => !comuns.has(h)).map((h) => (
                <span key={h} className="rounded-full border border-borda px-3 py-1.5 text-sm">{h}</span>
              ))}
            </div>
          </div>
        )}
        {cartao.bio && (
          <div>
            <p className="rotulo mb-2">Sobre</p>
            <p className="leading-relaxed">{cartao.bio}</p>
          </div>
        )}
      </div>
    </article>
  );
}
