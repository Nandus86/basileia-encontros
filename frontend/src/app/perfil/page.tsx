"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { CampoBio, EditorDeRevelacoes, EnviarFoto, Preferencias, SeletorDeHobbies, useCatalogoDeHobbies } from "@/components/campos-do-perfil";
import { Botao, Protegida, Tela } from "@/components/estrutura";
import { IconeLua, IconeSair, IconeSol, IconeTela } from "@/components/icones";
import { useSessao } from "@/contexts/sessao";
import { api } from "@/lib/api";
import { aplicarTema, lerTema, type Tema } from "@/lib/tema";
import type { MeuPerfil } from "@/types";

export default function Perfil() {
  return (
    <Protegida completo={false}>
      <Tela titulo="Meu perfil">
        <Conteudo />
      </Tela>
    </Protegida>
  );
}

function Conteudo() {
  const { perfil, atualizar, sair } = useSessao() as { perfil: MeuPerfil; atualizar: (p: MeuPerfil) => void; sair: () => void };
  const router = useRouter();
  const catalogo = useCatalogoDeHobbies();
  const [hobbies, setHobbies] = useState(perfil.hobbies);
  const [bio, setBio] = useState(perfil.bio);
  const [aviso, setAviso] = useState<{ texto: string; erro: boolean } | null>(null);
  const [salvando, setSalvando] = useState(false);
  const mudou = bio !== perfil.bio || hobbies.join("|") !== perfil.hobbies.join("|");

  async function salvar() {
    setAviso(null);
    setSalvando(true);
    try {
      atualizar(await api.mudarEu({ hobbies, bio }));
      setAviso({ texto: "Perfil salvo.", erro: false });
    } catch (e) {
      setAviso({ texto: e instanceof Error ? e.message : "Não consegui salvar.", erro: true });
    } finally {
      setSalvando(false);
    }
  }

  async function pausar(visivel: boolean) {
    try {
      atualizar(await api.mudarEu({ visivel }));
    } catch {}
  }

  return (
    <div className="space-y-8 pb-6">
      <section className="flex flex-col items-center text-center">
        <EnviarFoto perfil={perfil} aoMudar={atualizar} />
        <h2 className="mt-4 text-2xl font-extrabold">{perfil.nome_publico}, {perfil.idade}</h2>
        <p className="text-sm text-texto-2">{perfil.igreja}</p>
        <p className="mt-3 rounded-full bg-superficie-2 px-4 py-1.5 text-sm font-bold">
          Para os outros você é <span className="text-primaria">{perfil.simbolo} {perfil.codinome}</span>
        </p>
        <p className="mt-2 max-w-xs text-xs text-texto-2">
          No começo os outros veem só o seu codinome e os seus interesses. O resto você revela aos poucos.
        </p>
      </section>

      {!perfil.completo && (
        <p className="rounded-2xl bg-primaria/10 p-4 text-sm font-medium">
          Para receber sinais, escolha pelo menos {catalogo.minimo} hobbies e mande uma foto.
        </p>
      )}

      <section>
        <p className="rotulo mb-3">Hobbies</p>
        <SeletorDeHobbies escolhidos={hobbies} mudar={setHobbies} catalogo={catalogo.hobbies} />
      </section>

      <section>
        <p className="rotulo mb-3">Sobre mim</p>
        <CampoBio valor={bio} mudar={setBio} />
      </section>

      {(mudou || aviso) && (
        <div className="sticky bottom-24 z-10 space-y-2">
          {aviso && <p role="status" className={`rounded-xl px-4 py-3 text-sm font-medium ${aviso.erro ? "bg-perigo/10 text-perigo" : "bg-sucesso/10 text-sucesso"}`}>{aviso.texto}</p>}
          {mudou && (
            <Botao className="w-full shadow-cartao" disabled={salvando || hobbies.length < catalogo.minimo} onClick={salvar}>
              {salvando ? "Salvando…" : hobbies.length < catalogo.minimo ? `Escolha pelo menos ${catalogo.minimo} hobbies` : "Salvar alterações"}
            </Botao>
          )}
        </div>
      )}

      <section>
        <p className="rotulo mb-3">O que revelar e quando</p>
        <EditorDeRevelacoes perfil={perfil} aoMudar={atualizar} />
      </section>

      <section>
        <p className="rotulo mb-3">Quem quero conhecer</p>
        <Preferencias perfil={perfil} aoMudar={atualizar} />
      </section>

      <section>
        <p className="rotulo mb-3">Receber sinais</p>
        <label className="flex items-center justify-between gap-4 rounded-2xl border border-borda bg-superficie p-4">
          <span className="text-sm">
            <span className="block font-semibold">{perfil.visivel ? "Perfil ativo" : "Perfil pausado"}</span>
            <span className="text-texto-2">Pausado, você não recebe nem aparece em sinais novos. As conexões continuam.</span>
          </span>
          <input type="checkbox" role="switch" checked={perfil.visivel} onChange={(e) => pausar(e.target.checked)}
            className="size-6 shrink-0 accent-[var(--primaria)]" />
        </label>
      </section>

      <section>
        <p className="rotulo mb-3">Aparência</p>
        <EscolherTema />
      </section>

      <Botao variante="perigo" className="w-full" onClick={() => { sair(); router.replace("/entrar"); }}>
        <IconeSair className="size-5" /> Sair
      </Botao>
    </div>
  );
}

function EscolherTema() {
  // só aparece depois da sessão carregar (nunca no servidor), então dá para ler o tema direto
  const [tema, setTema] = useState<Tema>(lerTema);
  const opcoes: { valor: Tema; rotulo: string; Icone: typeof IconeSol }[] = [
    { valor: "sistema", rotulo: "Sistema", Icone: IconeTela },
    { valor: "claro", rotulo: "Claro", Icone: IconeSol },
    { valor: "escuro", rotulo: "Escuro", Icone: IconeLua },
  ];
  return (
    <div className="grid grid-cols-3 gap-2" role="radiogroup" aria-label="Tema">
      {opcoes.map(({ valor, rotulo, Icone }) => (
        <button key={valor} type="button" role="radio" aria-checked={tema === valor}
          onClick={() => { aplicarTema(valor); setTema(valor); }}
          className={`flex flex-col items-center gap-1.5 rounded-2xl border p-3 text-sm font-semibold ${
            tema === valor ? "border-primaria bg-primaria/10 text-primaria" : "border-borda bg-superficie"
          }`}>
          <Icone className="size-5" /> {rotulo}
        </button>
      ))}
    </div>
  );
}
