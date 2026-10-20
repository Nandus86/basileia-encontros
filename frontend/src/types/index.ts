export type ItemDeRevelacao = "sobre" | "nome" | "idade" | "bairro" | "chat" | "foto" | "igreja";

export type MeuPerfil = {
  id: number;
  nome: string;
  nome_publico: string;
  idade: number;
  genero: "feminino" | "masculino";
  cidade: string;
  bairro: string;
  igreja: string;
  hobbies: string[];
  bio: string;
  tem_foto: boolean;
  idade_min: number;
  idade_max: number;
  raio_km: number;
  visivel: boolean;
  completo: boolean;
  tem_localizacao: boolean;
  local_do_app: boolean;
  codinome: string;
  simbolo: string;
  jornada: number;
  revelacoes: { item: ItemDeRevelacao; rotulo: string; limite: number | null }[];
  limites_possiveis: number[];
};

/** A outra pessoa como eu a vejo: codinome e interesses sempre; o resto só se ela revelou. */
export type Publico = {
  id: number;
  codinome: string;
  simbolo: string;
  hobbies: string[];
  em_comum: string[];
  nome: string | null;
  idade: number | null;
  local: string | null;
  sobre: string | null;
  igreja: string | null;
  foto: boolean;
};

export type Sinal = Publico & { motivos: string[]; afinidade: "alta" | "media" | "baixa" | null };

export type MensagemChat = { id: number; texto: string; minha: boolean; criado_em: string };

export type EventoDaDupla = { tipo: string; titulo: string; pontos: number; sintonia: number; criado_em: string };

export type PerguntaADois = {
  atual: { id: number; texto: string; minha: string | null; dela: string | null } | null;
  volta_amanha: boolean;
  anterior: { texto: string; minha: string; dela: string } | null;   // a última que os dois responderam
};

export type ResumoDaConexao = {
  id: number;
  criado_em: string;
  outra: Publico;
  pontos: number;
  sintonia: number | null;
  chat_aberto: boolean;
  chat_abre_em: number | null;
  nivel_dela: string | null;
  proxima_descoberta: { rotulo: string; pontos: number } | null;
  ultima: MensagemChat | null;
  nao_lidas: number;
  pergunta_pendente: boolean;
};

export type MinhaRevelacao = {
  item: ItemDeRevelacao;
  rotulo: string;
  limite: number | null;
  revelado: boolean;
  na_mao: boolean;
};

export type DetalheDaConexao = Omit<ResumoDaConexao, "ultima" | "nao_lidas" | "pergunta_pendente"> & {
  minhas: MinhaRevelacao[];
  pergunta: PerguntaADois;
  eventos: EventoDaDupla[];
};

export type Jornada = {
  pontos: number;
  nivel: string;
  nivel_desde: number;
  proximo_nivel: string | null;
  proximo_em: number | null;
  sinais_por_dia: number;
  sequencia: number;
  profundidade: number;
  devocional_hoje: boolean;
  testes_feitos: number;
};

export type Devocional = {
  id: number;
  dia: string | null;
  titulo: string;
  referencia: string;
  reflexao: string;
  pergunta: string;
  minha: string | null;
};

export type ResumoDoTeste = { id: number; titulo: string; tema: string; questoes: number; feito: boolean };

export type Teste = ResumoDoTeste & { lista: { texto: string; opcoes: string[] }[] };

export type Conteudo = {
  id: number;
  tipo: "devocional" | "pergunta" | "teste";
  status: "pendente" | "aprovado" | "recusado";
  origem: string;
  dados: Record<string, unknown>;
  dia: string | null;
  criado_em: string;
};

export type Denuncia = {
  id: number;
  motivo: string;
  criado_em: string;
  de: { id: number; nome: string; igreja: string; codinome: string };
  sobre: { id: number; nome: string; igreja: string; codinome: string };
};

export type ContaDeTeste = { cpf: string; descricao: string };
