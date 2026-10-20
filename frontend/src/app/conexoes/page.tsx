"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Sintonia } from "@/components/afinidade";
import { Avatar } from "@/components/avatar";
import { Botao, Protegida, Tela } from "@/components/estrutura";
import { IconeConversa } from "@/components/icones";
import { api } from "@/lib/api";
import { nomeDe } from "@/lib/nomes";
import type { ResumoDaConexao } from "@/types";

export default function Conexoes() {
  return (
    <Protegida completo={false}>
      <Tela titulo="Conexões">
        <Lista />
      </Tela>
    </Protegida>
  );
}

function Lista() {
  const [lista, setLista] = useState<ResumoDaConexao[] | null>(null);
  const [erro, setErro] = useState("");

  useEffect(() => {
    let vivo = true;
    const carregar = () => api.conexoes().then((c) => vivo && setLista(c)).catch((e) => vivo && setErro(e.message));
    carregar();
    const id = setInterval(carregar, 10000);
    return () => {
      vivo = false;
      clearInterval(id);
    };
  }, []);

  if (erro && !lista) return <p role="alert" className="mt-6 text-center text-perigo">{erro}</p>;
  if (!lista) return <div className="mt-10 flex justify-center"><div className="size-8 animate-spin rounded-full border-4 border-borda border-t-primaria" /></div>;

  if (lista.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3 text-center">
        <IconeConversa className="size-10 text-destaque" />
        <h2 className="text-xl font-extrabold">Nenhuma conexão ainda</h2>
        <p className="text-texto-2">Quando alguém para quem você enviou sinal também enviar, a conexão aparece aqui.</p>
        <Link href="/sinais" className="mt-3"><Botao>Ver os sinais de hoje</Botao></Link>
      </div>
    );
  }

  return (
    <ul className="space-y-3 pb-4">
      {lista.map((c) => {
        const aviso = c.nao_lidas ? `${c.nao_lidas} mensagem(ns) nova(s)` : c.pergunta_pendente ? "Pergunta a dois esperando você"
          : c.chat_aberto ? (c.ultima ? `${c.ultima.minha ? "Você: " : ""}${c.ultima.texto}` : "Chat aberto — diga oi!")
          : c.proxima_descoberta ? `Próxima descoberta com ${c.proxima_descoberta.pontos} pts` : "";
        const destaque = c.nao_lidas > 0 || c.pergunta_pendente;
        return (
          <li key={c.id}>
            <Link href={`/conexoes/${c.id}`} className="flex items-center gap-3 rounded-3xl border border-borda bg-superficie p-3.5">
              <Avatar id={c.outra.id} nome={c.outra.codinome} simbolo={c.outra.simbolo} liberada={c.outra.foto} tamanho={56} />
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate font-bold">{nomeDe(c.outra)}</span>
                  <span className="shrink-0 text-sm font-extrabold text-primaria">{c.pontos} pts</span>
                </div>
                <p className={`truncate text-sm ${destaque ? "font-semibold text-texto" : "text-texto-2"}`}>{aviso}</p>
                <div className="mt-1.5 flex items-center gap-2">
                  <Sintonia valor={c.sintonia} />
                  {c.nivel_dela && <span className="text-xs text-texto-2">Nível {c.nivel_dela}</span>}
                  {destaque && <span className="ml-auto size-2.5 rounded-full bg-perigo" aria-label="novidade" />}
                </div>
              </div>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
