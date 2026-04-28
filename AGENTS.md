# AGENTS.md

## Objetivo

Este repositório contém o backend do EloMind, uma API em FastAPI para fluxos de terapia digital. O projeto cobre autenticação, convites, vínculo terapeuta-cliente, reflexões, feedback terapêutico com apoio de IA, anamnese, sonhos, consentimento, tokens de push e solicitação de exclusão de dados.

Este documento serve para agentes e colaboradores técnicos que precisem analisar, alterar, testar ou estender o sistema com segurança.

## Resumo Rápido

- Stack principal: FastAPI + SQLAlchemy ORM + MySQL + JWT + SMTP + OpenAI.
- Ponto de entrada: `app/main.py`.
- Banco: configurado por `DATABASE_URL` em `app/config.py`.
- Criação de tabelas: automática no startup com `Base.metadata.create_all(bind=engine)`.
- Não há migrations versionadas no repositório.
- Os testes presentes hoje são scripts manuais em `app/test/`, não uma suíte estruturada de `pytest`.
- O código mistura comentários em português, mensagens de erro em português/inglês e alguns arquivos com problemas de encoding visíveis.

## Estrutura do Projeto

```text
app/
  main.py                    # criação da aplicação FastAPI e include_router
  config.py                  # leitura de variáveis de ambiente
  db/
    base.py                  # declarative base e registro de models
    session.py               # engine e SessionLocal
  core/
    deps.py                  # autenticação atual via bearer token
    security.py              # hash de senha e JWT
    email.py                 # envio SMTP
    logger.py                # logger para IA
    invite_tokens.py         # utilitário de convites
  services/
    ia_service.py            # integração com OpenAI para feedback estruturado
  modules/
    auth/
    users/
    invitations/
    consents/
    reflections/
    feedback/
    anamnesis/
    dreams/
    push_tokens/
    data_deletion_requests/
    therapist_clients/
  test/
    test_email.py            # script manual de teste SMTP
    test_push.py             # script manual de teste Expo Push
```

## Como Rodar

### Ambiente virtual

No Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

No Linux/macOS:

```bash
source .venv/bin/activate
```

### Instalação

```powershell
pip install -r requirements.txt
```

### Subir a API

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Healthcheck

`GET /health`

### Documentação interativa

- Swagger UI: `/docs`
- ReDoc: `/redoc`

## Variáveis de Ambiente Conhecidas

Definidas ou consumidas diretamente no código atual:

- `DATABASE_URL`
- `JWT_SECRET`
- `JWT_ALGORITHM`
- `JWT_EXPIRE_MINUTES`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `SMTP_HOST`
- `SMTP_PORT`
- `ADMIN_KEY`

### Observações importantes

- `DATABASE_URL` tem fallback para MySQL local `elomind`.
- `JWT_SECRET` tem fallback inseguro (`CHANGE_ME`), então produção exige override.
- `OPENAI_MODEL` hoje cai em `gpt-4o-mini` se não configurado.
- `SMTP_HOST` e `SMTP_PORT` são lidos, mas `app/core/email.py` hoje usa `smtp.gmail.com:587` fixos no código.
- `app/config.py` imprime configuração SMTP no import. Isso é aceitável em dev, mas é um cuidado para produção.

## Arquitetura Atual

### Fluxo HTTP

O padrão predominante por módulo é:

1. `router.py` recebe a request, resolve `Depends`, valida papel de usuário e traduz exceções.
2. `service.py` concentra a regra de negócio.
3. `model.py` define entidades SQLAlchemy.
4. `schemas.py` define os contratos Pydantic.

### Banco e ORM

- O engine SQLAlchemy é criado em `app/db/session.py`.
- A sessão é entregue por `get_db()`.
- Os models são registrados em `app/db/base.py` via imports explícitos.
- O schema é criado automaticamente no startup; isso facilita o MVP, mas aumenta risco de drift entre ambientes.

### Autenticação

- O login gera JWT com `sub=email`.
- `get_current_user()` em `app/core/deps.py`:
  - lê token bearer,
  - decodifica JWT,
  - busca usuário por email,
  - bloqueia usuário inativo com `403`.
- Os papéis válidos são `client` e `therapist`.

## Mapa dos Módulos

### `auth`

Arquivos:

- `app/modules/auth/router.py`
- `app/modules/auth/service.py`
- `app/modules/auth/schemas.py`
- `app/modules/auth/password_reset/*`

Responsabilidades:

- `POST /auth/signup`
- `POST /auth/login`
- `GET /auth/me`
- `POST /auth/forgot-password`
- `POST /auth/reset-password`

Notas:

- O reset de senha evita enumeração de email no endpoint de início.
- O token de reset é persistido em hash SHA-256.
- Expiração atual: 30 minutos.
- O router de password reset possui fallback local de `send_email` com `print` se a importação falhar.

### `users`

Responsabilidades:

- `GET /users/clients`
- `PATCH /users/{user_id}/status`

Notas:

- Fluxo restrito a terapeuta.
- Só clientes podem ser ativados/desativados.
- Terapeuta não pode alterar o próprio status.

### `invitations`

Responsabilidades:

- `POST /invitations`
- `GET /invitations/validate`
- `POST /invitations/signup`

Notas:

- O convite é criado por terapeuta.
- O email de convite é enviado via `app/core/email.py`.
- O signup por convite também estabelece o vínculo terapeuta-cliente.

### `consents`

Responsabilidades:

- `GET /consents/me`
- `POST /consents`

Notas:

- Fluxo client-only.
- O aceite é binário; `accepted` precisa ser `true`.

### `reflections`

Responsabilidades:

- Cliente:
  - `POST /reflections/`
  - `GET /reflections/me`
  - `PATCH /reflections/{reflection_id}`
  - `DELETE /reflections/{reflection_id}`
- Terapeuta:
  - `GET /reflections/pending`
  - `GET /reflections/{reflection_id}`

Notas:

- A reflection tenta associar automaticamente o terapeuta do cliente.
- Há lógica de push para avisar terapeuta quando uma reflexão é criada/atualizada.
- Edição/exclusão é bloqueada quando já existe feedback aprovado.

### `feedback`

Responsabilidades:

- `POST /feedback/generate/{reflection_id}`
- `GET /feedback/pending`
- `PATCH /feedback/{feedback_id}/approve`
- `PATCH /feedback/{feedback_id}/reject`
- `GET /feedback/therapist/by-reflection/{reflection_id}`
- `GET /feedback/by-client/{client_id}`
- `GET /feedback/by-reflection/{reflection_id}`

Notas:

- Status identificados no serviço:
  - `pending_approval`
  - `approved`
  - `rejected`
- A geração usa `app/services/ia_service.py`.
- O serviço tenta usar anamnese como contexto de apoio.
- Aprovação dispara notificação push ao cliente.

### `anamnesis`

Responsabilidades:

- `POST /anamnesis/{client_id}`
- `GET /anamnesis/{client_id}`
- `PATCH /anamnesis/{client_id}`

Notas:

- Fluxo therapist-only.
- O terapeuta precisa ser dono do cliente vinculado.
- Há uma `UniqueConstraint` por cliente/terapeuta no model.

### `dreams`

Responsabilidades:

- Cliente:
  - `POST /dreams`
- Terapeuta:
  - `GET /dreams/{client_id}`
  - `PATCH /dreams/{dream_id}`

Notas:

- O cliente cadastra o sonho, mas não existe endpoint de leitura para ele.
- O terapeuta só acessa sonhos dos próprios clientes.

### `push_tokens`

Responsabilidades:

- `POST /push-tokens/`
- `GET /push-tokens/me`
- `POST /push-tokens/deactivate`

Notas:

- Guarda token Expo por usuário e plataforma.
- É usado por fluxos de reflexão e aprovação de feedback.

### `data_deletion_requests`

Responsabilidades:

- `POST /data-deletion-request`
- `GET /data-deletion-request`
- `POST /admin/data-deletion-execute/{client_id}`

Notas:

- O endpoint admin usa header `X-Admin-Key`.
- A exclusão total remove dados ligados ao cliente e depois o próprio usuário.
- O serviço tenta marcar a solicitação como `completed` antes da remoção final.

### `therapist_clients`

Responsabilidade:

- Entidade de vínculo entre terapeuta e cliente.
- O serviço atual expõe utilitário de linkagem usado pelos convites.

## Integrações Externas

### OpenAI

Arquivo principal: `app/services/ia_service.py`

Função central:

- `generate_feedback_structured(...)`

Comportamento:

- Gera JSON com `feedback`, `neuro_tip` e `activity`.
- Faz pós-validação da resposta do modelo.
- Possui fallbacks locais quando a resposta vier fora do formato esperado.
- Grava logs em `logs/ia_service.log`.

Cuidados:

- O arquivo contém bastante regra de negócio embutida em texto e validações heurísticas.
- Há sinais de texto com encoding corrompido em comentários e strings.
- Mudanças nesse serviço devem ser validadas com cuidado porque impactam qualidade clínica, fallback e estrutura da resposta.

### SMTP

Arquivo principal: `app/core/email.py`

Comportamento:

- Usa `smtplib` com TLS.
- Hoje conecta fixamente em Gmail.

Cuidados:

- Ainda não respeita `SMTP_HOST`/`SMTP_PORT` dinamicamente.
- Pode falhar em ambientes com provedores SMTP diferentes.

### Push Notifications

Uso atual:

- Há envio para Expo em fluxos de reflexão/feedback.
- Existe script manual `app/test/test_push.py` para teste direto.

## Convenções de Código Observadas

### O que o projeto já faz

- Separação razoável entre router, service, schemas e model.
- Dependências de autenticação resolvidas por `Depends`.
- Regras de autorização localizadas nos routers ou helpers de papel.
- Tipagem parcial com `list[...]` e modelos Pydantic.

### O que preservar ao editar

- Manter o padrão por módulo: `router.py`, `service.py`, `schemas.py`, `model.py`.
- Colocar regra de negócio em `service.py` sempre que possível.
- Deixar os routers mais finos, focados em IO HTTP.
- Reutilizar `get_current_user()` e helpers de papel em vez de duplicar verificação de token.
- Reaproveitar a `Session` passada por `Depends(get_db)`.

### Inconsistências atuais que um agente deve respeitar ao tocar

- Há mensagens de erro em português e em inglês.
- Alguns endpoints têm prefixo no router e outros recebem prefixo no `main.py`.
- O projeto não usa migrations formais.
- Há prints de debug no código de produção.
- Alguns arquivos exibem encoding quebrado; evite reformatar em massa sem necessidade.

## Comandos Úteis

### Procurar arquivos

```powershell
rg --files
```

### Procurar símbolos ou endpoints

```powershell
rg -n "APIRouter|include_router|def .*route|@router" app
```

### Subir o servidor

```powershell
uvicorn app.main:app --reload
```

### Testar scripts manuais

```powershell
python app/test/test_email.py
python app/test/test_push.py
```

## Estratégia de Mudança Recomendada

### Ao criar um novo módulo

1. Criar `model.py`, `schemas.py`, `service.py` e `router.py`.
2. Registrar o model em `app/db/base.py`.
3. Incluir o router em `app/main.py`.
4. Validar papel do usuário com `Depends`.
5. Definir claramente se o endpoint é client-only, therapist-only ou admin-only.

### Ao alterar comportamento de banco

1. Conferir se a mudança depende de coluna nova ou alteração de schema.
2. Como não há migrations, avaliar impacto de `create_all`.
3. Verificar se a alteração quebra ambiente já populado.
4. Evitar confiar apenas em criação automática para mudanças destrutivas ou renomeações.

### Ao alterar auth ou security

1. Conferir `app/core/security.py`.
2. Conferir `app/core/deps.py`.
3. Conferir impacto em `signup`, `login` e `/auth/me`.
4. Validar usuários inativos e papel (`client`/`therapist`).

### Ao alterar IA/feedback

1. Validar saída estruturada esperada.
2. Preservar fallback quando OpenAI falhar.
3. Conferir efeitos colaterais de aprovação e push.
4. Evitar quebrar compatibilidade do schema retornado ao app cliente.

## Checklist de Verificação Antes de Finalizar Mudanças

- O router novo ou alterado foi incluído em `app/main.py`?
- O model novo foi importado em `app/db/base.py`?
- O endpoint respeita autenticação e autorização corretas?
- O serviço comete `commit()` só quando realmente necessário?
- Mensagens de erro sensíveis evitam vazamento de informação?
- O fluxo continua funcionando com usuário `client` e `therapist`?
- Se a mudança toca IA, o fallback continua íntegro?
- Se a mudança toca exclusão de dados, a ordem dos deletes continua segura?
- O código novo não expôs segredo em logs ou prints?

## Riscos e Débitos Técnicos Conhecidos

- Não há migrations versionadas.
- `Base.metadata.create_all()` no startup pode mascarar problemas de schema e não substitui migração real.
- `README.md` atual é mínimo e não documenta operação.
- `run.sh` parece desalinhado com este ambiente:
  - usa `venv/bin/activate`, mas o repositório contém `.venv/`;
  - termina com `pause`, o que não faz sentido em shell bash puro.
- `app/core/email.py` ignora `SMTP_HOST` e `SMTP_PORT` lidos em config.
- `app/config.py` faz `print` no import.
- Existem scripts de teste manuais, mas não uma suíte automatizada robusta.
- Há texto com encoding quebrado em vários arquivos.
- Há bastante lógica de domínio e integração misturada em alguns serviços longos, especialmente `feedback` e `ia_service`.

## Boas Práticas Para Agentes

- Faça alterações pequenas e localizadas.
- Não normalize encoding em massa junto com mudanças funcionais.
- Antes de editar um fluxo, leia router + service + model + schema do módulo correspondente.
- Em mudanças de domínio, confirme se existe dependência cruzada com:
  - `feedback`
  - `reflections`
  - `anamnesis`
  - `therapist_clients`
  - `push_tokens`
- Se precisar introduzir migrations, trate isso como uma mudança arquitetural separada.

## Sugestões de Evolução

- Introduzir Alembic para migrations.
- Criar suíte real com `pytest` e banco isolado para testes.
- Centralizar autorização por papéis.
- Remover prints de debug e padronizar logging.
- Corrigir encoding dos arquivos.
- Fazer `app/core/email.py` respeitar host/porta do ambiente.
- Separar melhor regras de integração de push/OpenAI dos serviços de domínio.

## Estado Atual Observado Durante a Análise

- Worktree Git sem mudanças locais no momento da análise.
- Arquivo de documentação principal (`README.md`) quase vazio.
- Repositório adequado para receber documentação operacional mais forte, e este `AGENTS.md` passa a cumprir esse papel para agentes técnicos.

