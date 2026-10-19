"use client";

import { useEffect, useState } from "react";
import { carregarFoto } from "@/lib/api";
import { IconeCadeado } from "./icones";

/* Tons do roxo do Basiléia: cada pessoa ganha um, sempre o mesmo. */
const TONS = [
  ["#7c3aed", "#4c1d95"],
  ["#8b5cf6", "#5b21b6"],
  ["#a855f7", "#6b21a8"],
  ["#6366f1", "#3730a3"],
  ["#c026d3", "#701a75"],
  ["#9333ea", "#3b0764"],
];

export function tom(id: number) {
  const [a, b] = TONS[id % TONS.length];
  return `linear-gradient(145deg, ${a}, ${b})`;
}

/** A foto só aparece quando liberada (ou é a própria). Antes disso: a inicial e um cadeado. */
export function Avatar({ id, nome, liberada, tamanho = 48, recarregar = 0, quadrado = false }: {
  id: number;
  nome: string;
  liberada: boolean;
  tamanho?: number;
  recarregar?: number;
  quadrado?: boolean;
}) {
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    let vivo = true;
    if (liberada) carregarFoto(id, recarregar > 0).then((u) => vivo && setUrl(u));
    return () => {
      vivo = false;
    };
  }, [id, liberada, recarregar]);

  const mostrar = liberada && url;
  return (
    <div className={`relative shrink-0 overflow-hidden text-white ${quadrado ? "rounded-3xl" : "rounded-full"}`} style={{
      width: tamanho, height: tamanho, background: mostrar ? undefined : tom(id),
    }}>
      {mostrar ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={url} alt={`Foto de ${nome}`} className="size-full object-cover" />
      ) : (
        <span className="flex size-full items-center justify-center font-bold"
          style={{ fontSize: tamanho * 0.42 }}>
          {nome.charAt(0).toUpperCase()}
        </span>
      )}
      {!liberada && tamanho >= 40 && (
        <span className="absolute right-0 bottom-0 flex items-center justify-center rounded-full bg-black/45"
          style={{ width: tamanho * 0.36, height: tamanho * 0.36 }} title="Foto ainda não liberada">
          <IconeCadeado className="size-[60%]" />
        </span>
      )}
    </div>
  );
}
