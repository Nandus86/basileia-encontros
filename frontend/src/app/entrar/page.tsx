"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Botao, Logo } from "@/components/estrutura";
import { IconeCadeado, IconeBrilho, IconeEscudo } from "@/components/icones";
import { useSessao } from "@/contexts/sessao";
import { api } from "@/lib/api";
import type { ContaDeTeste } from "@/types";

function mascaraCpf(valor: string) {
  const d = valor.replace(/\D/g, "").slice(0, 11);
  return d
    .replace(/^(\d{3})(\d)/, "$1.$2")
    .replace(/^(\d{3})\.(\d{3})(\d)/, "$1.$2.$3")
    .replace(/\.(\d{3})(\d)/, ".$1-$2");
}

export default function Entrar() {
  const { pronta, token, perfil, abrir } = useSessao();
  const router = useRouter();
  const [cpf, setCpf] = useState("");
  const [senha, setSenha] = useState("");
  const [igrejas, setIgrejas] = useState<{ igreja_id: string; igreja_nome: string }[]>([]);
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [contasDeTeste, setContasDeTeste] = useState<ContaDeTeste[]>([]);

  useEffect(() => {
    if (pronta && token && perfil) router.replace(perfil.completo ? "/descobrir" : "/boas-vindas");
  }, [pronta, token, perfil, router]);

  useEffect(() => {
    api.saude().then((s) => {
      if (s.demo) api.contasDeTeste().then(setContasDeTeste);
    }).catch(() => {});
  }, []);

  async function enviar(usuario = cpf, chave = senha, igrejaId?: string) {
    setErro("");
    setEnviando(true);
    try {
      const r = await api.entrar(usuario, chave, igrejaId);
      if ("escolher" in r) setIgrejas(r.escolher);
      else {
        abrir(r.token, r.perfil);
        router.replace(r.perfil.completo ? "/descobrir" : "/boas-vindas");
      }
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Não foi possível entrar agora.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-dvh max-w-md flex-col px-5 pt-[max(env(safe-area-inset-top),2.5rem)] pb-8">
      <Logo />
      <h1 className="mt-10 text-3xl leading-tight font-extrabold tracking-tight">
        Conheça alguém que <span className="text-primaria">caminha na mesma fé</span>.
      </h1>
      <p className="mt-3 text-texto-2">Só para membros solteiros e maiores de idade das igrejas no Basiléia.</p>

      <ul className="mt-6 space-y-3 text-sm">
        <li className="flex gap-3"><IconeBrilho className="size-5 shrink-0 text-destaque" />
          A IA aproxima quem tem os mesmos interesses e mora perto.</li>
        <li className="flex gap-3"><IconeCadeado className="size-5 shrink-0 text-destaque" />
          Sua foto fica escondida: você libera só na conversa, se quiser.</li>
        <li className="flex gap-3"><IconeEscudo className="size-5 shrink-0 text-destaque" />
          Todo mundo aqui é membro com cadastro na igreja.</li>
      </ul>

      {igrejas.length > 0 ? (
        <section className="surgir mt-8">
          <p className="rotulo mb-3">Escolha a igreja</p>
          <div className="space-y-2">
            {igrejas.map((i) => (
              <Botao key={i.igreja_id} variante="secundario" className="w-full justify-start" disabled={enviando}
                onClick={() => enviar(cpf, senha, i.igreja_id)}>
                {i.igreja_nome}
              </Botao>
            ))}
          </div>
        </section>
      ) : (
        <form className="mt-8 space-y-4" onSubmit={(e) => { e.preventDefault(); enviar(); }}>
          <label className="block">
            <span className="mb-1.5 block text-sm font-semibold">CPF</span>
            <input value={cpf} onChange={(e) => setCpf(mascaraCpf(e.target.value))} inputMode="numeric"
              autoComplete="username" placeholder="000.000.000-00" required
              className="h-13 w-full rounded-2xl border border-borda bg-superficie px-4 text-lg outline-none focus:border-primaria" />
          </label>
          <label className="block">
            <span className="mb-1.5 block text-sm font-semibold">Senha</span>
            <input value={senha} onChange={(e) => setSenha(e.target.value)} type="password" autoComplete="current-password"
              placeholder="Por enquanto, o seu CPF" required
              className="h-13 w-full rounded-2xl border border-borda bg-superficie px-4 text-lg outline-none focus:border-primaria" />
          </label>
          {erro && <p role="alert" className="rounded-xl bg-perigo/10 px-4 py-3 text-sm font-medium text-perigo">{erro}</p>}
          <Botao type="submit" className="w-full" disabled={enviando}>{enviando ? "Entrando…" : "Entrar"}</Botao>
        </form>
      )}

      {contasDeTeste.length > 0 && igrejas.length === 0 && (
        <section className="mt-8 rounded-2xl border border-dashed border-borda p-4">
          <p className="rotulo mb-3">Modo demonstração</p>
          <div className="space-y-1">
            {contasDeTeste.map((c) => (
              <button key={c.cpf} type="button" disabled={enviando}
                onClick={() => { setCpf(mascaraCpf(c.cpf)); setSenha(c.cpf); enviar(c.cpf, c.cpf); }}
                className="block w-full rounded-xl px-3 py-2 text-left text-sm hover:bg-superficie-2">
                {c.descricao}
              </button>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
