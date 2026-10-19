"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useSessao } from "@/contexts/sessao";
import { api } from "@/lib/api";
import { IconeBussola, IconeConversa, IconeUsuario } from "./icones";

export function Logo({ pequeno = false }: { pequeno?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <div className={`flex items-center justify-center rounded-xl bg-primaria font-black text-sobre-primaria ${pequeno ? "size-8 text-lg" : "size-11 text-2xl"}`}>
        B
      </div>
      <div className="leading-none">
        <div className={`font-extrabold tracking-tight ${pequeno ? "text-lg" : "text-2xl"}`}>Basiléia</div>
        <div className={`font-semibold text-destaque ${pequeno ? "text-xs" : "text-sm"}`}>Encontros</div>
      </div>
    </div>
  );
}

export function Carregando() {
  return (
    <div className="flex min-h-dvh items-center justify-center" role="status" aria-label="Carregando">
      <div className="size-9 animate-spin rounded-full border-4 border-borda border-t-primaria" />
    </div>
  );
}

/** Páginas de quem já entrou. `completo`: manda para o cadastro quem ainda não terminou o perfil. */
export function Protegida({ children, completo = true }: { children: React.ReactNode; completo?: boolean }) {
  const { pronta, token, perfil } = useSessao();
  const router = useRouter();
  const falta = pronta && (!token ? "/entrar" : perfil && completo && !perfil.completo ? "/boas-vindas" : null);

  useEffect(() => {
    if (falta) router.replace(falta);
  }, [falta, router]);

  if (!pronta || !perfil || falta) return <Carregando />;
  return <>{children}</>;
}

const ABAS = [
  { href: "/descobrir", rotulo: "Descobrir", Icone: IconeBussola },
  { href: "/conversas", rotulo: "Conversas", Icone: IconeConversa },
  { href: "/perfil", rotulo: "Perfil", Icone: IconeUsuario },
];

/** Mensagens novas no ícone de Conversas (confere a cada 20 s; leve o bastante para o MVP). */
function useNaoLidas() {
  const [total, setTotal] = useState(0);
  useEffect(() => {
    let vivo = true;
    const conferir = () =>
      api.matches().then((ms) => vivo && setTotal(ms.reduce((s, m) => s + m.nao_lidas, 0))).catch(() => {});
    conferir();
    const id = setInterval(conferir, 20000);
    return () => {
      vivo = false;
      clearInterval(id);
    };
  }, []);
  return total;
}

export function BarraDeAbas() {
  const caminho = usePathname();
  const naoLidas = useNaoLidas();
  return (
    <nav className="pb-seguro fixed inset-x-0 bottom-0 z-20 border-t border-borda bg-superficie/95 backdrop-blur">
      <ul className="mx-auto flex max-w-md justify-around">
        {ABAS.map(({ href, rotulo, Icone }) => {
          const ativa = caminho.startsWith(href);
          return (
            <li key={href}>
              <Link href={href} aria-current={ativa ? "page" : undefined}
                className={`relative flex min-w-20 flex-col items-center gap-1 px-3 pt-2.5 pb-1 text-xs font-semibold ${ativa ? "text-primaria" : "text-texto-2"}`}>
                <Icone className="size-6" />
                {rotulo}
                {href === "/conversas" && naoLidas > 0 && (
                  <span className="absolute top-1.5 right-4 min-w-5 rounded-full bg-perigo px-1.5 text-center text-[11px] leading-5 text-white">
                    {naoLidas > 9 ? "9+" : naoLidas}
                  </span>
                )}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

export function Tela({ titulo, acao, children, abas = true }: {
  titulo?: React.ReactNode;
  acao?: React.ReactNode;
  children: React.ReactNode;
  abas?: boolean;
}) {
  return (
    <div className={`mx-auto flex min-h-dvh max-w-md flex-col ${abas ? "pb-24" : ""}`}>
      {titulo !== undefined && (
        <header className="sticky top-0 z-10 flex items-center justify-between bg-fundo/90 px-4 pt-[max(env(safe-area-inset-top),0.75rem)] pb-3 backdrop-blur">
          {typeof titulo === "string" ? <h1 className="text-2xl font-extrabold tracking-tight">{titulo}</h1> : titulo}
          {acao}
        </header>
      )}
      <main className="flex flex-1 flex-col px-4">{children}</main>
      {abas && <BarraDeAbas />}
    </div>
  );
}

export function Botao({ variante = "primario", className = "", ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variante?: "primario" | "secundario" | "fantasma" | "perigo";
}) {
  const estilos = {
    primario: "bg-primaria text-sobre-primaria hover:bg-primaria-forte",
    secundario: "border border-borda bg-superficie text-texto hover:bg-superficie-2",
    fantasma: "text-texto-2 hover:bg-superficie-2",
    perigo: "border border-perigo/40 text-perigo hover:bg-perigo/10",
  }[variante];
  return (
    <button {...props}
      className={`inline-flex min-h-12 items-center justify-center gap-2 rounded-2xl px-5 font-semibold transition disabled:opacity-50 ${estilos} ${className}`} />
  );
}
