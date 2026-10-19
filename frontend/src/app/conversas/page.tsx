"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Avatar } from "@/components/avatar";
import { Botao, Protegida, Tela } from "@/components/estrutura";
import { IconeConversa } from "@/components/icones";
import { api } from "@/lib/api";
import type { Match } from "@/types";

export default function Conversas() {
  return (
    <Protegida>
      <Tela titulo="Conversas">
        <Lista />
      </Tela>
    </Protegida>
  );
}

function quando(iso: string) {
  const d = new Date(iso);
  const hoje = new Date();
  if (d.toDateString() === hoje.toDateString()) return d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
}

function Lista() {
  const [matches, setMatches] = useState<Match[] | null>(null);
  const [erro, setErro] = useState("");

  useEffect(() => {
    let vivo = true;
    const carregar = () => api.matches().then((m) => vivo && setMatches(m)).catch((e) => vivo && setErro(e.message));
    carregar();
    const id = setInterval(carregar, 10000);
    return () => {
      vivo = false;
      clearInterval(id);
    };
  }, []);

  if (erro && !matches) return <p role="alert" className="mt-6 text-center text-perigo">{erro}</p>;
  if (!matches) return <div className="mt-10 flex justify-center"><div className="size-8 animate-spin rounded-full border-4 border-borda border-t-primaria" /></div>;

  if (matches.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3 text-center">
        <IconeConversa className="size-10 text-destaque" />
        <h2 className="text-xl font-extrabold">Nenhum match ainda</h2>
        <p className="text-texto-2">Quando alguém que você curtiu também curtir você, a conversa aparece aqui.</p>
        <Link href="/descobrir" className="mt-3"><Botao>Descobrir pessoas</Botao></Link>
      </div>
    );
  }

  const novos = matches.filter((m) => !m.ultima);
  const comConversa = matches.filter((m) => m.ultima);
  return (
    <div className="space-y-6 pb-4">
      {novos.length > 0 && (
        <section>
          <p className="rotulo mb-3">Novos matches</p>
          <div className="-mx-4 flex gap-4 overflow-x-auto px-4 pb-1">
            {novos.map((m) => (
              <Link key={m.id} href={`/conversas/${m.id}`} className="flex w-18 shrink-0 flex-col items-center gap-1.5">
                <Avatar id={m.pessoa.id} nome={m.pessoa.nome} liberada={m.foto_liberada} tamanho={64} />
                <span className="w-full truncate text-center text-sm font-semibold">{m.pessoa.nome}</span>
              </Link>
            ))}
          </div>
        </section>
      )}
      {comConversa.length > 0 && (
        <section>
          <p className="rotulo mb-1">Mensagens</p>
          <ul className="divide-y divide-borda">
            {comConversa.map((m) => (
              <li key={m.id}>
                <Link href={`/conversas/${m.id}`} className="flex items-center gap-3 py-3">
                  <Avatar id={m.pessoa.id} nome={m.pessoa.nome} liberada={m.foto_liberada} tamanho={56} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-baseline justify-between gap-2">
                      <span className="font-bold">{m.pessoa.nome}</span>
                      <span className="shrink-0 text-xs text-texto-2">{quando(m.ultima!.criado_em)}</span>
                    </div>
                    <div className="flex items-center justify-between gap-2">
                      <p className={`truncate text-sm ${m.nao_lidas ? "font-semibold text-texto" : "text-texto-2"}`}>
                        {m.ultima!.minha ? "Você: " : ""}{m.ultima!.texto}
                      </p>
                      {m.nao_lidas > 0 && (
                        <span className="min-w-5 shrink-0 rounded-full bg-primaria px-1.5 text-center text-xs leading-5 font-bold text-sobre-primaria">
                          {m.nao_lidas}
                        </span>
                      )}
                    </div>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
