# TEST_CRYPTO_MANUAL.md

## Objetivo

Validar que:

- os campos sensíveis são criptografados antes de salvar no banco;
- a API continua retornando plaintext para o cliente;
- campos não sensíveis continuam sem criptografia;
- o fluxo com IA continua funcionando usando reflection e anamnese descriptografadas.

## Smoke Test Rápido

Use esta sequência quando quiser validar o essencial em poucos minutos:

1. Criar terapeuta e cliente vinculado pelos endpoints de auth e convite.
2. Criar uma reflection com texto sensível.
3. Rodar `SELECT` em `reflections` e confirmar ciphertext começando com `gAAAA`.
4. Rodar `GET /reflections/me` e confirmar plaintext.
5. Criar uma anamnese e conferir ciphertext em `anamnesis`.
6. Gerar feedback com IA para a reflection e conferir ciphertext em `feedback`.
7. Buscar o feedback pela API e confirmar plaintext.
8. Criar um dream, atualizar notas do terapeuta e conferir ciphertext em `dreams`.

Se esse fluxo passar, a criptografia de campo está funcionando no caminho crítico principal.

## Pré-requisitos

- Reiniciar a API após configurar `FIELD_ENCRYPTION_KEY` no `.env`.
- Confirmar que o backend está subindo sem erro.
- Confirmar acesso ao banco definido em `DATABASE_URL`.
- Ter um cliente HTTP disponível, como Swagger, Insomnia ou Postman.
- Ter acesso ao MySQL para rodar `SELECT` de conferência.

## Convenções usadas neste teste

Substitua estes placeholders ao executar:

- `TOKEN_TERAPEUTA`
- `TOKEN_CLIENTE`
- `TOKEN_CLIENTE_VINCULADO`
- `CLIENT_ID`
- `REFLECTION_ID`
- `DREAM_ID`
- `FEEDBACK_ID`
- `TOKEN_DO_CONVITE`

## 1. Criar terapeuta

Request:

```http
POST /auth/signup
Content-Type: application/json

{
  "email": "terapeuta.crypto@elomind.com",
  "name": "Terapeuta Crypto",
  "role": "therapist",
  "password": "Teste@123"
}
```

Esperado:

- status `200`
- retorno com `access_token`

Guarde o token como `TOKEN_TERAPEUTA`.

## 2. Criar cliente comum

Request:

```http
POST /auth/signup
Content-Type: application/json

{
  "email": "cliente.crypto@elomind.com",
  "name": "Cliente Crypto",
  "role": "client",
  "password": "Teste@123"
}
```

Esperado:

- status `200`
- retorno com `access_token`

Guarde o token como `TOKEN_CLIENTE`.

## 3. Criar vínculo terapeuta-cliente pelo fluxo real de convite

### 3.1 Criar convite

```http
POST /invitations
Authorization: Bearer TOKEN_TERAPEUTA
Content-Type: application/json

{
  "email": "cliente.vinculado.crypto@elomind.com"
}
```

Esperado:

- status `200`
- `ok=true`

### 3.2 Validar convite

```http
GET /invitations/validate?token=TOKEN_DO_CONVITE
```

Esperado:

- `valid=true`

### 3.3 Finalizar signup do cliente vinculado

```http
POST /invitations/signup
Content-Type: application/json

{
  "token": "TOKEN_DO_CONVITE",
  "name": "Cliente Vinculado Crypto",
  "password": "Teste@123"
}
```

### 3.4 Login do cliente vinculado

```http
POST /auth/login
Content-Type: application/json

{
  "email": "cliente.vinculado.crypto@elomind.com",
  "password": "Teste@123"
}
```

Guarde o token como `TOKEN_CLIENTE_VINCULADO`.

## 4. Descobrir o `client_id`

```http
GET /auth/me
Authorization: Bearer TOKEN_CLIENTE_VINCULADO
```

Esperado:

- status `200`
- retorno com o `id` do cliente

Use esse valor como `CLIENT_ID`.

## 5. Teste de Reflection

### 5.1 Criar reflection

```http
POST /reflections/
Authorization: Bearer TOKEN_CLIENTE_VINCULADO
Content-Type: application/json

{
  "feeling_after_session": "Saí da sessão mais leve, mas ainda com ansiedade sobre meu trabalho.",
  "what_learned": "Percebi que eu me cobro demais quando erro em reuniões.",
  "positive_point": "Consegui dormir melhor duas noites nesta semana.",
  "resistance_or_disagreement": "Ainda não concordo totalmente com reduzir meu ritmo no trabalho."
}
```

Esperado na API:

- status `201`
- todos os campos textuais retornados em plaintext

Guarde o `id` como `REFLECTION_ID`.

### 5.2 Conferir no banco

```sql
SELECT
  id,
  feeling_after_session,
  what_learned,
  positive_point,
  resistance_or_disagreement
FROM reflections
ORDER BY id DESC
LIMIT 1;
```

Esperado no banco:

- os valores textuais devem estar como ciphertext
- normalmente começam com `gAAAA`
- o conteúdo não deve aparecer legível

### 5.3 Ler via API

```http
GET /reflections/me
Authorization: Bearer TOKEN_CLIENTE_VINCULADO
```

Esperado:

- os textos voltam legíveis
- não deve aparecer `gAAAA...`

### 5.4 Atualizar reflection

```http
PATCH /reflections/REFLECTION_ID
Authorization: Bearer TOKEN_CLIENTE_VINCULADO
Content-Type: application/json

{
  "feeling_after_session": "Saí da sessão mais calma, mas ainda preocupada com minhas entregas.",
  "what_learned": "Entendi que tenho dificuldade em reconhecer meus limites.",
  "positive_point": "Consegui pedir ajuda em uma tarefa importante.",
  "resistance_or_disagreement": "Ainda acho difícil desacelerar sem culpa."
}
```

Esperado:

- resposta em plaintext
- banco continua com ciphertext

## 6. Teste de Anamnese

### 6.1 Criar anamnese

```http
POST /anamnesis/CLIENT_ID
Authorization: Bearer TOKEN_TERAPEUTA
Content-Type: application/json

{
  "summary": "Cliente relata histórico de insônia, autocobrança intensa e conflito frequente com a mãe."
}
```

Esperado:

- status `200`
- `summary` retornado legível

### 6.2 Conferir no banco

```sql
SELECT
  id,
  client_id,
  therapist_id,
  summary
FROM anamnesis
WHERE client_id = CLIENT_ID
ORDER BY id DESC
LIMIT 1;
```

Esperado:

- `summary` salvo como ciphertext

### 6.3 Ler via API

```http
GET /anamnesis/CLIENT_ID
Authorization: Bearer TOKEN_TERAPEUTA
```

Esperado:

- `summary` em plaintext

### 6.4 Atualizar anamnese

```http
PATCH /anamnesis/CLIENT_ID
Authorization: Bearer TOKEN_TERAPEUTA
Content-Type: application/json

{
  "summary": "Cliente relata insônia recorrente, alta autocobrança e conflitos familiares com impacto emocional."
}
```

Esperado:

- resposta legível
- banco segue com ciphertext

## 7. Teste de Dreams

### 7.1 Criar dream como cliente

```http
POST /dreams
Authorization: Bearer TOKEN_CLIENTE_VINCULADO
Content-Type: application/json

{
  "description": "Sonhei que estava preso em um elevador lotado e não conseguia pedir ajuda."
}
```

Esperado:

- resposta com `id` e `created_at`

Guarde o `id` como `DREAM_ID`.

### 7.2 Conferir no banco

```sql
SELECT
  id,
  description,
  therapist_tags,
  therapist_notes
FROM dreams
WHERE id = DREAM_ID;
```

Esperado:

- `description` criptografado
- `therapist_tags` e `therapist_notes` ainda podem estar `NULL`

### 7.3 Listar como terapeuta

```http
GET /dreams/CLIENT_ID
Authorization: Bearer TOKEN_TERAPEUTA
```

Esperado:

- `description` em plaintext

### 7.4 Atualizar dream como terapeuta

```http
PATCH /dreams/DREAM_ID
Authorization: Bearer TOKEN_TERAPEUTA
Content-Type: application/json

{
  "therapist_tags": "ansiedade, claustrofobia, impotencia",
  "therapist_notes": "Explorar sensacao de falta de controle e contextos recentes de pressao."
}
```

Esperado:

- retorno legível

### 7.5 Conferir no banco novamente

```sql
SELECT
  id,
  description,
  therapist_tags,
  therapist_notes
FROM dreams
WHERE id = DREAM_ID;
```

Esperado:

- os três campos textuais devem estar criptografados

## 8. Teste de Feedback com IA

### 8.1 Gerar feedback

```http
POST /feedback/generate/REFLECTION_ID
Authorization: Bearer TOKEN_TERAPEUTA
```

Esperado:

- resposta com:
  - `ia_generated_content`
  - `ia_neuro_nutrition_tip`
  - `ia_activity_suggestion`
- tudo retornado em plaintext

Guarde o `id` como `FEEDBACK_ID`.

### 8.2 Conferir no banco

```sql
SELECT
  id,
  reflection_id,
  ia_generated_content,
  ia_neuro_nutrition_tip,
  ia_activity_suggestion,
  therapist_notes,
  status
FROM feedback
WHERE id = FEEDBACK_ID;
```

Esperado:

- campos textuais salvos como ciphertext
- `status` continua em texto normal

### 8.3 Aprovar com edição

```http
PATCH /feedback/FEEDBACK_ID/approve
Authorization: Bearer TOKEN_TERAPEUTA
Content-Type: application/json

{
  "ia_generated_content": "Você citou ansiedade no trabalho e muita autocobrança após reuniões. Também apareceu um ponto positivo importante: dormir melhor em duas noites. Como essas pequenas melhoras podem ser ampliadas na sua rotina?",
  "ia_neuro_nutrition_tip": "Manter hidratacao regular ao longo do dia pode ajudar o corpo a sustentar melhor energia e atencao.",
  "ia_activity_suggestion": "Faca uma caminhada leve de 10 minutos apos o expediente para reduzir a tensao acumulada.",
  "therapist_notes": "Reforcar vinculo entre autocobranca e exaustao nas proximas sessoes."
}
```

Esperado:

- retorno em plaintext

### 8.4 Buscar como terapeuta

```http
GET /feedback/therapist/by-reflection/REFLECTION_ID
Authorization: Bearer TOKEN_TERAPEUTA
```

Esperado:

- todos os campos textuais legíveis

### 8.5 Buscar como cliente

```http
GET /feedback/by-reflection/REFLECTION_ID
Authorization: Bearer TOKEN_CLIENTE_VINCULADO
```

Esperado:

- cliente vê o feedback aprovado em plaintext

### 8.6 Conferir no banco após aprovação

```sql
SELECT
  ia_generated_content,
  ia_neuro_nutrition_tip,
  ia_activity_suggestion,
  therapist_notes,
  status,
  therapist_approved_by,
  approved_at
FROM feedback
WHERE id = FEEDBACK_ID;
```

Esperado:

- os campos textuais continuam criptografados
- `status`, `therapist_approved_by` e `approved_at` permanecem sem criptografia

## 9. Compatibilidade com dados antigos

Se houver um registro antigo salvo sem criptografia:

- faça um `GET` por um endpoint normal;
- confira que a API continua devolvendo o texto normalmente;
- confirme que não há erro ao ler valores legacy em plaintext.

## 10. Checklist final

Marque como concluído quando tudo abaixo for verdadeiro:

- reflection salva ciphertext no banco e plaintext na API
- anamnese salva ciphertext no banco e plaintext na API
- dreams salvam ciphertext no banco e plaintext na API
- feedback salva ciphertext no banco e plaintext na API
- campos não sensíveis continuam legíveis no banco:
  - `id`
  - `client_id`
  - `therapist_id`
  - `reflection_id`
  - `status`
  - `created_at`
  - `updated_at`
  - `approved_at`
  - `therapist_approved_by`
- geração de feedback com IA continua funcionando
- updates não quebram leitura
- dados antigos sem criptografia continuam compatíveis
