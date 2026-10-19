"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { CampoBio, EnviarFoto, Preferencias, SeletorDeHobbies, useCatalogoDeHobbies } from "@/components/campos-do-perfil";
import { Botao, Logo, Protegida } from "@/components/estrutura";
import { IconeBrilho, IconeCadeado, IconeConversa } from "@/components/icones";
import { useSessao } from "@/contexts/sessao";
import { api } from "@/lib/api";
import type { MeuPerfil } from "@/types";

const PASSOS = ["Boas-vindas", "Hobbies", "Sobre você", "Foto", "Preferências"];

export default function BoasVindas() {
  return (
    <Protegida completo={false}>
      <Cadastro />
    </Protegida>
  );
}

function Cadastro() {
  const { perfil, atualizar } = useSessao() as { perfil: MeuPerfil; atualizar: (p: MeuPerfil) => void };
  const router = useRouter();
  const catalogo = useCatalogoDeHobbies();
  const [passo, setPasso] = useState(0);
  const [hobbies, setHobbies] = useState<string[]>(perfil.hobbies);
  const [bio, setBio] = useState(perfil.bio);
  const [erro, setErro] = useState("");
  const [salvando, setSalvando] = useState(false);

  async function avancar() {
    setErro("");
    setSalvando(true);
    try {
      if (passo === 1) atualizar(await api.mudarEu({ hobbies }));
      if (passo === 2) atualizar(await api.mudarEu({ bio }));
      if (passo === PASSOS.length - 1) return router.replace("/descobrir");
      setPasso(passo + 1);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Não consegui salvar.");
    } finally {
      setSalvando(false);
    }
  }

  const pode = passo === 1 ? hobbies.length >= catalogo.minimo : passo === 3 ? perfil.tem_foto : true;

  return (
    <div className="mx-auto flex min-h-dvh max-w-md flex-col px-5 pt-[max(env(safe-area-inset-top),1.25rem)]">
      <div className="flex items-center justify-between">
        <Logo pequeno />
        <span className="text-sm font-semibold text-texto-2">{passo + 1} de {PASSOS.length}</span>
      </div>
      <div className="mt-4 flex gap-1.5" aria-hidden="true">
        {PASSOS.map((p, i) => (
          <span key={p} className={`h-1.5 flex-1 rounded-full ${i <= passo ? "bg-primaria" : "bg-borda"}`} />
        ))}
      </div>

      <main key={passo} className="surgir flex-1 py-8">
        {passo === 0 && (
          <>
            <h1 className="text-3xl font-extrabold tracking-tight">Que bom ter você aqui, {perfil.nome_publico}!</h1>
            <p className="mt-3 text-texto-2">
              {perfil.idade} anos · {perfil.cidade || "cidade não informada"} · {perfil.igreja}
            </p>
            <p className="mt-1 text-xs text-texto-2">Esses dados vêm do cadastro da igreja. Para mudar, fale com a secretaria.</p>
            <ul className="mt-8 space-y-5">
              <li className="flex gap-4">
                <IconeBrilho className="size-7 shrink-0 text-primaria" />
                <div><p className="font-semibold">Afinidade de verdade</p>
                  <p className="text-sm text-texto-2">A IA só mostra quem tem os mesmos interesses que você e mora perto.</p></div>
              </li>
              <li className="flex gap-4">
                <IconeCadeado className="size-7 shrink-0 text-primaria" />
                <div><p className="font-semibold">Sua foto fica guardada</p>
                  <p className="text-sm text-texto-2">Ninguém vê sua foto no Descobrir. Depois do match, você decide se libera na conversa.</p></div>
              </li>
              <li className="flex gap-4">
                <IconeConversa className="size-7 shrink-0 text-primaria" />
                <div><p className="font-semibold">Conversa só com match</p>
                  <p className="text-sm text-texto-2">Só dá para conversar quando os dois curtiram. Mostramos só o seu primeiro nome.</p></div>
              </li>
            </ul>
          </>
        )}
        {passo === 1 && (
          <>
            <h1 className="text-2xl font-extrabold tracking-tight">Do que você gosta?</h1>
            <p className="mt-2 mb-6 text-texto-2">Escolha pelo menos {catalogo.minimo}. É com eles que a IA acha quem combina com você.</p>
            <SeletorDeHobbies escolhidos={hobbies} mudar={setHobbies} catalogo={catalogo.hobbies} />
          </>
        )}
        {passo === 2 && (
          <>
            <h1 className="text-2xl font-extrabold tracking-tight">Conte um pouco sobre você</h1>
            <p className="mt-2 mb-6 text-texto-2">Onde serve, o que gosta de fazer, o que procura. Sem telefone ou redes sociais.</p>
            <CampoBio valor={bio} mudar={setBio} />
          </>
        )}
        {passo === 3 && (
          <>
            <h1 className="text-2xl font-extrabold tracking-tight">Sua foto</h1>
            <p className="mt-2 mb-8 text-texto-2">
              Ela <strong className="text-texto">não aparece</strong> para ninguém no Descobrir. Só quem der match com você
              e receber a sua liberação na conversa.
            </p>
            <EnviarFoto perfil={perfil} aoMudar={atualizar} />
          </>
        )}
        {passo === 4 && (
          <>
            <h1 className="text-2xl font-extrabold tracking-tight">Quem você quer conhecer</h1>
            <p className="mt-2 mb-6 text-texto-2">Dá para mudar quando quiser no seu perfil.</p>
            <Preferencias perfil={perfil} aoMudar={atualizar} />
          </>
        )}
      </main>

      <footer className="pb-seguro sticky bottom-0 space-y-2 bg-fundo pt-3 pb-4">
        {erro && <p role="alert" className="rounded-xl bg-perigo/10 px-4 py-3 text-sm font-medium text-perigo">{erro}</p>}
        <div className="flex gap-3">
          {passo > 0 && <Botao variante="secundario" onClick={() => setPasso(passo - 1)}>Voltar</Botao>}
          <Botao className="flex-1" disabled={!pode || salvando} onClick={avancar}>
            {passo === 0 ? "Começar" : passo === 2 && !bio ? "Pular" : passo === PASSOS.length - 1 ? "Ver quem combina comigo" : "Continuar"}
          </Botao>
        </div>
      </footer>
    </div>
  );
}
