# Regras de conteúdo — EscleroVida (@esclero_vida)

Toda arte e toda legenda seguem estas regras. Na dúvida, não publique: avise o responsável.

## Quem somos
- A EscleroVida leva o **tratamento de varizes** aos **municípios parceiros**, em parceria com as prefeituras, **pelo SUS e sem custo para o paciente**.
- Municípios parceiros (BA): **Barra do Choça, Bom Jesus da Serra, Caculé, Itororó e Planalto**. Atualize esta lista quando mudar.
- Atendimento **sem internação**, em **sessões rápidas**. A equipe de cirurgiões vasculares vai até o município, com material próprio.
- Como ser atendido: o paciente procura o **posto de saúde (unidade de saúde) da sua cidade**; a unidade encaminha; **o agendamento é feito pela Secretaria Municipal de Saúde**.
- A EscleroVida **não agenda** pelo Instagram, direct, WhatsApp ou telefone.
- Procedimento no SUS (SIGTAP): **Tratamento esclerosante não estético de varizes dos membros inferiores** (03.09.07.001-5 unilateral / 03.09.07.002-3 bilateral). A indicação é definida caso a caso pelo cirurgião vascular.
- Responsável Técnico: **Dr. Vinicius Guerra — Cirurgião Vascular — CRM-BA 29908 — RQE 23546**.
- Site: esclerovida.com.br

## Nunca usar
- **"vasinhos", "telangiectasias", "escleroterapia de vasinhos"** ou qualquer referência a tratamento estético, beleza, "pernas bonitas" ou aparência. Não fazemos tratamento estético.
- A palavra "estético(a)" só pode aparecer na forma **"não estético"**.
- A hashtag #escleroterapia (é muito associada a tratamento estético).
- Promessas de resultado: cura, definitivo, garantido, sem dor, 100%, milagre. Sensacionalismo ou comparação com outros serviços.
- Preços, fotos de pacientes, depoimentos, "antes e depois".
- Diagnóstico ou orientação individual ("se você tem X, faça Y"), indicação de remédios, pomadas ou receitas caseiras.
- Meias de compressão só podem ser citadas como **"com orientação de um profissional de saúde"**.
- Estatísticas ou números que não estejam nesta página ou em PAUTAS.md.
- Convite para agendar pelo direct, WhatsApp ou telefone.

## Sempre
- Falar de **varizes**: veias dilatadas, tortuosas e salientes, geralmente nas pernas.
- Usar só os fatos desta página e os "Fatos" da pauta escolhida em PAUTAS.md.
- Quando o tema for sinais, sintomas ou atendimento, orientar: **procure o posto de saúde da sua cidade**; o agendamento é feito pela Secretaria Municipal de Saúde.
- Feridas que não cicatrizam: orientar a procurar a unidade de saúde.
- Tom informativo, acolhedor e direto, em português simples e frases curtas.
- O rodapé do Responsável Técnico já sai na arte (o gerador inclui). Na legenda do feed, incluir no fim:
  `Responsável Técnico: Dr. Vinicius Guerra | Cirurgião Vascular | CRM-BA 29908 | RQE 23546`

## Formato
- **12h — post de feed** (1080×1350) com legenda.
- **19h — story** (1080×1920), sem legenda.
- Título: 2 ou 3 linhas curtas (até ~18 caracteres por linha no story e ~22 no feed). A última linha leva `*` no início para ficar em destaque.
- Listas: 3 a 5 itens de até ~34 caracteres. Parágrafo do layout "texto": até ~220 caracteres.
- `cta` padrão: "Procure o posto de saúde da sua cidade". `nota` padrão: "O agendamento é feito pela Secretaria Municipal de Saúde." (ou "Atendimento pelo SUS, sem custo, nos municípios parceiros.").
- Legenda do feed: 500 a 1.000 caracteres, parágrafos curtos, até 3 emojis, a linha do RT e 6 a 10 hashtags entre: #varizes #saudevascular #circulacao #SUS #saudedaspernas #BarraDoChoca #BomJesusDaSerra #Cacule #Itororo #PlanaltoBA #Bahia

## Conferência antes de publicar
1. `python3 gerador/render.py pauta.json arte.jpg --legenda legenda.txt` (feed) ou sem `--legenda` (story). O script recusa termos proibidos, legenda sem a linha do RT e texto que não cabe.
2. Abrir a imagem e conferir: texto legível, nada cortado, ortografia e acentos corretos.
