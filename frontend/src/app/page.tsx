"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Carregando } from "@/components/estrutura";
import { useSessao } from "@/contexts/sessao";

export default function Inicio() {
  const { pronta, token, perfil } = useSessao();
  const router = useRouter();

  useEffect(() => {
    if (!pronta) return;
    if (!token || !perfil) router.replace("/entrar");
    else router.replace(perfil.completo ? "/sinais" : "/boas-vindas");
  }, [pronta, token, perfil, router]);

  return <Carregando />;
}
