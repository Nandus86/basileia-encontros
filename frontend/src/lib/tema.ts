export type Tema = "sistema" | "claro" | "escuro";

const CHAVE = "encontros:tema";

/** Roda antes da página aparecer (no <head>), para não piscar o tema errado. */
export const SCRIPT_DO_TEMA = `try{var t=localStorage.getItem("${CHAVE}");if(t==="claro"||t==="escuro")document.documentElement.dataset.tema=t}catch(e){}`;

export function lerTema(): Tema {
  try {
    const t = localStorage.getItem(CHAVE);
    return t === "claro" || t === "escuro" ? t : "sistema";
  } catch {
    return "sistema";
  }
}

export function aplicarTema(tema: Tema) {
  const html = document.documentElement;
  if (tema === "sistema") delete html.dataset.tema;
  else html.dataset.tema = tema;
  try {
    if (tema === "sistema") localStorage.removeItem(CHAVE);
    else localStorage.setItem(CHAVE, tema);
  } catch {}
}
