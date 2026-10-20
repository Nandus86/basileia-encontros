"use client";

/** Os pontos da dupla numa trilha, com os marcos (o que se revela em cada ponto). */
export function TrilhaDePontos({ pontos, marcos }: { pontos: number; marcos: { pontos: number; rotulo: string }[] }) {
  const fim = Math.max(500, ...marcos.map((m) => m.pontos + 50), pontos + 50);
  const pct = (v: number) => `${Math.min(100, (v / fim) * 100)}%`;
  const unicos = Array.from(new Map(marcos.map((m) => [m.pontos, m])).values());
  return (
    <div className="pt-6 pb-2" role="img" aria-label={`${pontos} pontos de afinidade`}>
      <div className="relative h-3 rounded-full bg-superficie-2">
        <div className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-primaria to-destaque transition-all"
          style={{ width: pct(pontos) }} />
        {unicos.map((m) => (
          <div key={m.pontos} className="absolute -top-6 -translate-x-1/2 text-center" style={{ left: pct(m.pontos) }}
            title={m.rotulo}>
            <span className={`block text-[10px] font-bold ${pontos >= m.pontos ? "text-primaria" : "text-texto-2"}`}>{m.pontos}</span>
            <span className={`mx-auto mt-1 block size-2.5 rounded-full border-2 ${pontos >= m.pontos ? "border-primaria bg-primaria" : "border-texto-2 bg-superficie"}`} />
          </div>
        ))}
      </div>
    </div>
  );
}

export function Sintonia({ valor }: { valor: number | null }) {
  if (valor === null) return null;
  return (
    <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${valor >= 85 ? "bg-primaria text-sobre-primaria" : "bg-superficie-2 text-texto-2"}`}>
      Sintonia {valor}%
    </span>
  );
}
