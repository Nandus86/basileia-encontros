"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, configurarSessao, esquecerFotos } from "@/lib/api";
import type { MeuPerfil } from "@/types";

const CHAVE = "encontros:token";

type Sessao = {
  pronta: boolean;
  token: string | null;
  perfil: MeuPerfil | null;
  abrir: (token: string, perfil: MeuPerfil) => void;
  atualizar: (perfil: MeuPerfil) => void;
  sair: () => void;
};

const Contexto = createContext<Sessao | null>(null);

function lerToken(): string | null {
  try {
    return localStorage.getItem(CHAVE);
  } catch {
    return null;
  }
}

function gravarToken(token: string | null) {
  try {
    if (token) localStorage.setItem(CHAVE, token);
    else localStorage.removeItem(CHAVE);
  } catch {}
}

export function SessaoProvider({ children }: { children: React.ReactNode }) {
  const [pronta, setPronta] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [perfil, setPerfil] = useState<MeuPerfil | null>(null);

  const sair = useCallback(() => {
    gravarToken(null);
    esquecerFotos();
    configurarSessao(null, () => {});
    setToken(null);
    setPerfil(null);
  }, []);

  useEffect(() => {
    // o token fica no aparelho; o perfil vem sempre da API (e confirma que o token ainda vale)
    let vivo = true;
    async function retomar() {
      const guardado = lerToken();
      if (guardado) {
        configurarSessao(guardado, sair);
        try {
          const p = await api.eu();
          if (vivo) {
            setToken(guardado);
            setPerfil(p);
          }
        } catch {
          sair();
        }
      }
      if (vivo) setPronta(true);
    }
    retomar();
    return () => {
      vivo = false;
    };
  }, [sair]);

  const abrir = useCallback(
    (novo: string, p: MeuPerfil) => {
      gravarToken(novo);
      configurarSessao(novo, sair);
      setToken(novo);
      setPerfil(p);
    },
    [sair],
  );

  const valor = useMemo(
    () => ({ pronta, token, perfil, abrir, atualizar: setPerfil, sair }),
    [pronta, token, perfil, abrir, sair],
  );
  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function useSessao(): Sessao {
  const s = useContext(Contexto);
  if (!s) throw new Error("useSessao fora do SessaoProvider");
  return s;
}
