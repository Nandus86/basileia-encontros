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
};

export type Afinidade = {
  nivel: "alta" | "media" | "baixa";
  proximidade: "perto" | "razoavel" | "longe";
  origem: "jev" | "llm" | "regras";
};

/** Como outra pessoa aparece: primeiro nome, distância arredondada e sem foto. */
export type Cartao = {
  id: number;
  nome: string;
  idade: number;
  cidade: string;
  igreja: string;
  distancia_km: number | null;
  hobbies: string[];
  em_comum: string[];
  bio: string;
  afinidade: Afinidade | null;
};

export type MensagemChat = {
  id: number;
  texto: string;
  minha: boolean;
  criado_em: string;
};

export type Match = {
  id: number;
  criado_em: string;
  pessoa: Cartao;
  foto_liberada: boolean;
  eu_liberei: boolean;
  ultima: MensagemChat | null;
  nao_lidas: number;
};

export type ContaDeTeste = { cpf: string; descricao: string };
