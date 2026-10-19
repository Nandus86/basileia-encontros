"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { MeuPerfil } from "@/types";
import { Avatar } from "./avatar";
import { Botao } from "./estrutura";
import { IconeCamera, IconeLocal } from "./icones";

export const TAMANHO_BIO = 300;

export function useCatalogoDeHobbies() {
  const [catalogo, setCatalogo] = useState<{ hobbies: string[]; minimo: number }>({ hobbies: [], minimo: 3 });
  useEffect(() => {
    api.hobbies().then(setCatalogo).catch(() => {});
  }, []);
  return catalogo;
}

export function SeletorDeHobbies({ escolhidos, mudar, catalogo, maximo = 10 }: {
  escolhidos: string[];
  mudar: (h: string[]) => void;
  catalogo: string[];
  maximo?: number;
}) {
  return (
    <div className="flex flex-wrap gap-2" role="group" aria-label="Hobbies">
      {catalogo.map((h) => {
        const marcado = escolhidos.includes(h);
        return (
          <button key={h} type="button" aria-pressed={marcado}
            disabled={!marcado && escolhidos.length >= maximo}
            onClick={() => mudar(marcado ? escolhidos.filter((x) => x !== h) : [...escolhidos, h])}
            className={`rounded-full border px-3.5 py-2 text-sm font-medium transition disabled:opacity-40 ${
              marcado ? "border-primaria bg-primaria text-sobre-primaria" : "border-borda bg-superficie hover:border-primaria"
            }`}>
            {h}
          </button>
        );
      })}
    </div>
  );
}

export function CampoBio({ valor, mudar }: { valor: string; mudar: (v: string) => void }) {
  return (
    <label className="block">
      <textarea value={valor} onChange={(e) => mudar(e.target.value.slice(0, TAMANHO_BIO))} rows={4}
        placeholder="Ex.: Sirvo no louvor, amo um café depois do culto e uma trilha no sábado."
        className="w-full resize-none rounded-2xl border border-borda bg-superficie p-4 outline-none focus:border-primaria" />
      <span className="mt-1 block text-right text-xs text-texto-2">{valor.length}/{TAMANHO_BIO}</span>
    </label>
  );
}

/** Reduz no celular antes de mandar (menos dados móveis); o servidor reabre e tira o EXIF de novo. */
async function reduzir(arquivo: File, lado = 1280): Promise<Blob> {
  try {
    const bitmap = await createImageBitmap(arquivo, { imageOrientation: "from-image" });
    const escala = Math.min(1, lado / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(bitmap.width * escala);
    canvas.height = Math.round(bitmap.height * escala);
    canvas.getContext("2d")!.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    return await new Promise((ok, falha) => canvas.toBlob((b) => (b ? ok(b) : falha()), "image/jpeg", 0.85));
  } catch {
    return arquivo;
  }
}

export function EnviarFoto({ perfil, aoMudar }: { perfil: MeuPerfil; aoMudar: (p: MeuPerfil) => void }) {
  const entrada = useRef<HTMLInputElement>(null);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState("");
  const [versao, setVersao] = useState(0);

  async function escolher(arquivo?: File) {
    if (!arquivo) return;
    setErro("");
    setEnviando(true);
    try {
      aoMudar(await api.mandarFoto(await reduzir(arquivo)));
      setVersao((v) => v + 1);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Não consegui mandar a foto.");
    } finally {
      setEnviando(false);
      if (entrada.current) entrada.current.value = "";
    }
  }

  return (
    <div className="flex flex-col items-center gap-4">
      <Avatar id={perfil.id} nome={perfil.nome_publico} liberada={perfil.tem_foto} tamanho={140} recarregar={versao} />
      <input ref={entrada} type="file" accept="image/jpeg,image/png,image/webp" className="hidden"
        onChange={(e) => escolher(e.target.files?.[0])} />
      <Botao variante={perfil.tem_foto ? "secundario" : "primario"} disabled={enviando}
        onClick={() => entrada.current?.click()}>
        <IconeCamera className="size-5" />
        {enviando ? "Enviando…" : perfil.tem_foto ? "Trocar foto" : "Escolher foto"}
      </Botao>
      {erro && <p role="alert" className="text-sm font-medium text-perigo">{erro}</p>}
    </div>
  );
}

export function Preferencias({ perfil, aoMudar }: { perfil: MeuPerfil; aoMudar: (p: MeuPerfil) => void }) {
  const [idadeMin, setIdadeMin] = useState(perfil.idade_min);
  const [idadeMax, setIdadeMax] = useState(perfil.idade_max);
  const [raio, setRaio] = useState(perfil.raio_km);
  const [aviso, setAviso] = useState("");
  const [buscandoLocal, setBuscandoLocal] = useState(false);

  async function salvar(campos: Parameters<typeof api.mudarEu>[0]) {
    setAviso("");
    try {
      aoMudar(await api.mudarEu(campos));
    } catch (e) {
      setAviso(e instanceof Error ? e.message : "Não consegui salvar.");
    }
  }

  function usarLocalizacao() {
    if (!navigator.geolocation) return setAviso("Seu navegador não informa a localização.");
    setBuscandoLocal(true);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          aoMudar(await api.mudarLocal(pos.coords.latitude, pos.coords.longitude));
          setAviso("Localização atualizada.");
        } catch (e) {
          setAviso(e instanceof Error ? e.message : "Não consegui salvar a localização.");
        } finally {
          setBuscandoLocal(false);
        }
      },
      () => {
        setBuscandoLocal(false);
        setAviso("Sem permissão para a localização. Usamos o endereço do cadastro da igreja.");
      },
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 600000 },
    );
  }

  const idade = "h-12 w-20 rounded-xl border border-borda bg-superficie text-center text-lg outline-none focus:border-primaria";
  return (
    <div className="space-y-6">
      <div>
        <p className="mb-2 font-semibold">Idade de quem quero conhecer</p>
        <div className="flex items-center gap-3">
          <input type="number" min={18} max={99} value={idadeMin} aria-label="Idade mínima" className={idade}
            onChange={(e) => setIdadeMin(Number(e.target.value))}
            onBlur={() => salvar({ idade_min: idadeMin, idade_max: idadeMax })} />
          <span className="text-texto-2">até</span>
          <input type="number" min={18} max={99} value={idadeMax} aria-label="Idade máxima" className={idade}
            onChange={(e) => setIdadeMax(Number(e.target.value))}
            onBlur={() => salvar({ idade_min: idadeMin, idade_max: idadeMax })} />
          <span className="text-texto-2">anos</span>
        </div>
      </div>
      <div>
        <div className="mb-2 flex justify-between font-semibold">
          <span>Distância máxima</span>
          <span className="text-primaria">{raio} km</span>
        </div>
        <input type="range" min={5} max={150} step={5} value={raio} aria-label="Distância máxima em km"
          className="w-full accent-[var(--primaria)]" onChange={(e) => setRaio(Number(e.target.value))}
          onPointerUp={() => salvar({ raio_km: raio })} onKeyUp={() => salvar({ raio_km: raio })} />
      </div>
      <div className="rounded-2xl border border-borda bg-superficie p-4">
        <div className="flex items-start gap-3">
          <IconeLocal className="mt-0.5 size-5 shrink-0 text-destaque" />
          <div className="text-sm">
            <p className="font-semibold">{perfil.cidade || "Cidade não informada"}{perfil.bairro ? ` · ${perfil.bairro}` : ""}</p>
            <p className="text-texto-2">
              {perfil.local_do_app ? "Localização do celular (aproximada, ~1 km)." :
                perfil.tem_localizacao ? "Do endereço no cadastro da igreja." : "Sem localização: só aparece quem é da mesma cidade."}
            </p>
          </div>
        </div>
        <Botao variante="secundario" className="mt-3 w-full" disabled={buscandoLocal} onClick={usarLocalizacao}>
          {buscandoLocal ? "Buscando…" : "Usar a localização do celular"}
        </Botao>
      </div>
      {aviso && <p role="status" className="text-sm text-texto-2">{aviso}</p>}
    </div>
  );
}
