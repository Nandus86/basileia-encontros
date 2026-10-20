/** Como chamar a outra pessoa: o codinome, e o primeiro nome junto quando ela já revelou. */
export function nomeDe(outra: { nome: string | null; codinome: string }) {
  return outra.nome ? `${outra.nome} · ${outra.codinome}` : outra.codinome;
}
