# Guia de estilo de código

Convenções de estilo do projeto `ha-metragen`. Antes de commitar, rode
`uv run ruff format --check .`, `uv run ruff check .` e
`uv run mypy custom_components/metragen` — todos devem terminar sem erros.
Em seguida vem o `uv run pytest` (com o gate de 90 % de cobertura).

**Sempre leia este arquivo antes de adicionar ou reestruturar código.**

## Idioma

O `hacs.json` declara `"country": ["BR"]`: a Metragen só existe no Brasil, então
o português do Brasil é o idioma do repositório.

- **Toda prosa lida por gente fica em pt-BR**: `README.md`, `CONTRIBUTING.md`,
  este guia, o `CLAUDE.md` e os demais `.md`; docstrings e comentários; o
  assunto e o corpo dos commits; títulos e descrições de PR; notas de release e
  `CHANGELOG.md`, inclusive os títulos de seção (`changelog-sections` no
  `release-please-config.json`); issues, comentários e reviews; os templates de
  issue e de PR em `.github/`; a descrição do repositório no GitHub e a
  `description` do `pyproject.toml`.
- **O código continua em inglês**: nomes de arquivo, de classe, de função e de
  variável, nomes de branch, chaves de dicionário, strings identificadoras e
  mensagens de log. O que uma ferramenta interpreta também é código: o tipo e o
  escopo do Conventional Commit (`feat(sensor): adiciona o consumo anual`), o
  rodapé `BREAKING CHANGE:`, os ids de workflow e de job, as labels.
- **Termos nativos do domínio não se traduzem**, nem no código nem na prosa —
  são a linguagem ubíqua compartilhada com os moradores e com o portal:
  `Medidor`, `Leitura`, `Anterior`, `AreaMorador`, `FiltroAno`. O que envolve o
  termo segue em inglês; identificadores perdem o acento, a prosa e as strings
  traduzidas o mantêm.
- O idioma da conversa com o usuário nunca decide o que vai para o disco.
- Strings voltadas ao usuário ficam apenas em
  `custom_components/metragen/translations/{en,pt-BR}.json` — nunca fixas no
  Python. O `en.json` continua obrigatório ao lado do `pt-BR.json`.

## Organização dos arquivos

- **Uma classe de nível superior por arquivo — inclusive TypedDicts e
  dataclasses.** Várias classes semanticamente relacionadas (famílias de
  exceções, entidades de sensor de uma plataforma, os payloads tipados e os
  dados de runtime) são agrupadas em um diretório de pacote, com uma classe por
  submódulo e um `__init__.py` que reexporta os símbolos públicos.
  - Exemplo: `exceptions/` contém `api_client_error.py`,
    `api_client_communication_error.py`, `api_client_authentication_error.py`,
    além do `__init__.py`.
  - Exemplo: `data/` contém `post.py`, `config_data.py`, `options_data.py`,
    `diagnostics_entry.py`, `diagnostics_payload.py`, `runtime.py`, além de um
    `__init__.py`. Todo TypedDict e toda dataclass ganha o próprio arquivo — um
    `data.py` plano com várias classes é dívida de migração, não um layout
    válido.
  - **Flexibilizações**: um TypedDict ou alias `type` consumido por um único
    módulo pode morar nesse módulo em vez de ter arquivo próprio, e dataclasses
    folha que descrevem fragmentos do mesmo payload podem dividir um módulo. O
    layout de pacote com uma classe por submódulo volta a ser o padrão assim
    que um formato é compartilhado entre módulos.
- **Aliases `type` são a exceção: moram em `data/__init__.py`**, junto das
  reexportações (`JsonPrimitive`, `JsonValue`, `JsonObject`,
  `MetragenConfigEntry`), e não em arquivos próprios.
- **Funções auxiliares** podem morar no mesmo arquivo da única classe que as
  usa (ex.: `_verify_response_or_raise` em `api.py`).
- **O `__init__.py` do pacote da integração** liga `async_setup_entry`,
  `async_unload_entry`, `async_reload_entry` e nada mais.

## Entidades: uma classe por entidade

- **Uma classe por entidade.** Toda entidade ganha a sua classe dedicada — nunca
  compartilhe uma classe genérica parametrizada por uma subclasse de
  `EntityDescription` com campos chamáveis como `value_fn` ou `action_fn`.
  Codifique o comportamento da entidade diretamente na classe, com `@property`
  e constantes `_attr_*` no nível da classe (ou uma instância simples de
  `EntityDescription` atribuída no nível da classe).
  - Não escreva uma subclasse `<DOMAIN><Platform>Description` com um campo
    `value_fn` / `action_fn`.
  - Escreva `<DOMAIN><Name><Platform>` (ex.: `MetragenStatusSensor`,
    `MetragenCancelButton`, `MetragenDoorBinarySensor`).
- O motivo: cada entidade é um contrato distinto; misturá-las em uma classe
  genérica esconde o contrato atrás de indireção e desestimula o refinamento
  por entidade (ícones, atributos de estado, lógica própria).
- **Os ícones das entidades ficam no `icons.json`**
  (`entity.<platform>.<translation_key>.default`), indexados pela
  `translation_key` da entidade — não em `_attr_icon`. O arquivo de ícones
  aceita variantes por estado e por faixa e mantém a apresentação fora do
  Python.

## Nomenclatura

- Classes públicas têm o prefixo `Metragen`.
- Entidades concretas de plataforma terminam com o tipo da entidade:
  `MetragenSensor`, `MetragenBinarySensor`,
  `MetragenSwitch`.
- Classes de exceção terminam com `Error`: `MetragenApiClientError`,
  `…CommunicationError`, `…AuthenticationError`.
- Atributos / funções privados têm o prefixo `_`.

## Tipagem

**Tipagem estrita. Sem genéricos, sem `Any`.** O mypy (`uv run mypy custom_components/metragen`) garante isso.

Proibidos: `typing.Any`, `object` como tipo de valor, `dict` / `list` / `tuple` /
`set` sem parâmetros, `dict[str, Any]`, `Mapping[str, Any]`.

Obrigatórios:

- `TypedDict` para formatos conhecidos de dict / JSON (veja no pacote `data/` os
  exemplos canônicos: `MetragenPost`, `MetragenConfigData`,
  `MetragenOptionsData`, `MetragenDiagnosticsPayload`,
  um por arquivo).
- `@dataclass` para registros estruturados (`MetragenData` em
  `data/runtime.py`).
- Aliases `type` nomeados para formatos recursivos / compartilhados —
  `JsonPrimitive`, `JsonValue`, `JsonObject` em `data/__init__.py`.
- `frozenset[str]` / `tuple[str, ...]` para coleções fixas de strings.
- `cast("TypedDictName", value)` nas fronteiras com o framework do HA que nos
  entregam um tipo permissivo (ex.: `entry.data` é `MappingProxyType[str, Any]`).

Ao restringir a assinatura de um callback fornecido pelo HA (ex.:
`async_step_user`), o mypy acusa `[override]` (violação de Liskov). Adicione
`# type: ignore[override]` com um comentário de uma linha explicando a
restrição deliberada — o `config_flow.py` traz o exemplo canônico.

## Properties e `__init__`

- **Prefira sempre `@property`** a atribuir valores `_attr_*` no `__init__`.
  Properties são calculadas sob demanda a partir dos campos guardados na classe
  pai (ex.: `self.coordinator`, `self.entity_description`).
- Quando o corpo do `__init__` só chamaria `super().__init__(...)`, omita o
  `__init__` e deixe o Python herdar o da classe pai.
- Constantes no nível da classe, como `_attr_attribution = ATTRIBUTION` e
  `_attr_has_entity_name = True`, são aceitáveis — não dependem do estado da
  instância.

## Imports

- Comece todo módulo com `from __future__ import annotations`, para que as
  anotações de tipo virem strings avaliadas sob demanda e o custo em runtime
  dos imports sob `if TYPE_CHECKING` seja zero.
- Imports relativos dentro do mesmo pacote (`from .module import …`) são o
  padrão.
- Mova os imports usados só para tipos para um bloco `TYPE_CHECKING` (Ruff
  `TC001`/`TC003`):

  ```python
  from __future__ import annotations
  from typing import TYPE_CHECKING

  if TYPE_CHECKING:
      from collections.abc import Mapping
      from .data import MetragenConfigData
  ```

- Comentários `noqa` ficam reservados a restrições inevitáveis do framework
  (ex.: `# noqa: ARG001` para parâmetros de callback do HA que precisam existir
  mas não são usados). Documente o motivo na própria linha se não for óbvio.
  Nunca silencie só para "deixar o ruff feliz" — corrija o código.

## Docstrings

- Toda classe, função e método públicos (inclusive `@property`) e todo
  `__init__` têm docstring. O Ruff exige isso por `D102`/`D107`.
- Docstrings são escritas em pt-BR. A regra `D401` do Ruff só conhece verbos em
  inglês e pode disparar por engano em uma primeira palavra portuguesa parecida
  com um verbo inglês ("Converte", "Helper"); reescreva a frase em vez de
  desligar a regra.
- Uma única frase costuma bastar. Descreva o *contrato* ou o *porquê*, não a
  implementação óbvia.
- Docstring de módulo no topo de todo arquivo `.py`.
- Evite repetir o tipo — a assinatura já faz isso.

## Comentários

- O padrão é **não comentar**. Adicione um comentário só quando o *porquê* não
  for óbvio pelo código: uma restrição oculta, um contorno, um invariante sutil
  ou uma sobreposição deliberada do sistema de tipos.
- Nunca descreva *o que* o código faz — identificadores bem nomeados cuidam
  disso.
- **Nada de divisores de seção** como `# --- API payloads ---` para agrupar
  declarações relacionadas. Se um arquivo tem tantas seções que você sente
  falta de separadores visuais, divida-o em vários arquivos.

## Logging

- Todo módulo usa o `LOGGER` do pacote, definido em `const.py`
  (`LOGGER: Logger = getLogger(__package__)`); nunca chame
  `logging.getLogger(...)` de forma avulsa.
- As mensagens de log são código e ficam em inglês.
- Use **formatação `%` preguiçosa**, nunca f-strings — elas forçam a
  interpolação mesmo quando o nível está filtrado:

  ```python
  LOGGER.warning("Refresh failed: %s", exception)   # ✓
  LOGGER.warning(f"Refresh failed: {exception}")    # ✗
  ```

- Níveis:
  - `debug` — resumos de buscas bem-sucedidas, diagnóstico de cada consulta.
  - `info` — ciclo de vida pontual (setup concluído, fluxo de reauth iniciado).
  - `warning` — falhas recuperáveis (erro transitório da API, uso de fallback).
  - `error` / `exception` — irrecuperável no ciclo atual; use `exception` com
    exceções capturadas dentro de blocos `except` para ter o traceback completo.
- Nunca logue segredos (`token`, `password`, `key`, headers completos). O
  mapeamento `Coordinator → UpdateFailed` deve engolir a forma em string da
  exceção original quando ela puder expô-los.

## Mensagens de erro

- Formato: `"Failed to <verb> <object>: <cause>"`, em que `<cause>` é a exceção
  ou um motivo curto. Mantenha-as curtas e fáceis de buscar com grep.
- Valide as entradas antes da chamada de rede, para que os erros mostrados ao
  usuário apontem para a entrada ruim e não para um traceback posterior
  (`config_flow._validate` rejeita credenciais malformadas antes de contatar a
  API).
- As exceções próprias seguem a mesma hierarquia:
  `MetragenApiClientError` (base) → `…CommunicationError` (timeout, conexão,
  DNS) e `…AuthenticationError` (401/403). Encapsule os erros brutos de origem
  na fronteira do cliente da API; tudo acima só captura a hierarquia própria.

## Coordinator e dados de runtime

- Todo o estado da API passa por `entry.runtime_data: MetragenData`
  (`data/runtime.py`). Nunca guarde estado da integração em `hass.data` — o
  `runtime_data` é descartado automaticamente no unload; o padrão legado
  `hass.data[DOMAIN][entry_id]`, não.
- O coordinator é tipado como `DataUpdateCoordinator[MetragenPost]` (ou o
  TypedDict que for o seu payload real). `_async_update_data` retorna o payload
  tipado.
- Use `await coordinator.async_config_entry_first_refresh()` durante o
  `async_setup_entry` (não `async_refresh()`) — uma primeira atualização que
  falha levanta `ConfigEntryNotReady`, e o HA tenta de novo com backoff
  automaticamente.
- Passe `always_update=False` ao coordinator quando o TypedDict do payload se
  compara bem com `__eq__`; o HA então pula os callbacks dos listeners e as
  escritas de estado quando os dados não mudaram.
- Use `self.async_contexts()` dentro de `_async_update_data` para limitar o
  trabalho de API às entidades inscritas no momento — entidades desabilitadas
  não devem gerar chamadas de rede.
- Mapeamento de erros dentro de `_async_update_data`:
  - Erros de comunicação → `raise UpdateFailed("Failed to …: %s" % err)`. Passe
    `retry_after=<seconds>` quando a origem sinalizar um backoff explícito (ex.:
    HTTP 429 `Retry-After`).
  - Erros de autenticação → `raise ConfigEntryAuthFailed(...)` — o HA cancela as
    próximas atualizações e inicia o fluxo `SOURCE_REAUTH`.
  - Nunca deixe strings brutas de exceções de origem chegarem ao `UpdateFailed`
    quando puderem carregar tokens; converta para uma mensagem sanitizada no
    cliente da API.

## Config / opções / reparos / diagnóstico

- O `config_flow.py` traz os passos `user`, `reauth`, `reauth_confirm` e
  `reconfigure`, todos compartilhando um helper `_validate` e um construtor
  `_credentials_schema`.
- O `options_flow.py` contém a única classe `MetragenOptionsFlow`. Novas chaves
  de opção entram no TypedDict `MetragenOptionsData`, em
  `data/options_data.py`.
- O `repairs.py` expõe `async_create_fix_flow`. Helpers de exemplo como
  `async_raise_deprecated_api_issue` mostram como registrar issues a partir de
  qualquer ponto da integração.
- O `diagnostics.py` retorna `MetragenDiagnosticsPayload`. As chaves sensíveis
  entram na constante `TO_REDACT: frozenset[str]`.

## Traduções

- Dois locales: `en.json` e `pt-BR.json`. O `tests/test_translations.py`
  parametriza sobre todos os locales e falha se os conjuntos de chaves
  aninhadas divergirem.
- As strings de issues ficam em `issues.<issue_id>`; as de opções, em
  `options.step.init.data`; as de fluxo, em `config.step.<step_id>`; os nomes
  de entidades, em `entity.<platform>.<key>.name`.

## Requisitos de publicação no HACS

O [HACS](https://www.hacs.xyz/docs/publish/integration/) valida o formato do
repositório a cada push via `hacs/action@main` (e o próprio HA roda o
`hassfest`). Os dois gates precisam ficar verdes:

- **Uma integração por repositório**, localizada em
  `custom_components/<domain>/`.
- O `manifest.json` deve declarar `domain`, `name`, `version`, `documentation`,
  `issue_tracker`, `codeowners`. A chave `version` é **obrigatória em
  integrações custom** (omita-a apenas em integrações do core) e precisa ser
  interpretável como `AwesomeVersion` — CalVer ou SemVer.
- O `manifest.json` também declara `integration_type`. JSON não aceita
  comentários, então a escolha fica registrada aqui: esta integração usa `hub`
  porque uma config entry representa uma conta do portal que expõe um
  dispositivo por medidor.
- O `hacs.json`, na raiz do repositório, fixa o core mínimo do HA pela chave
  `homeassistant`. Esse é o terceiro pin do HA (veja o `CLAUDE.md`).
- O `hacs.json` declara `"country": ["BR"]` (ISO 3166-1 alpha-2). Quem define
  um país nas opções do HACS deixa de ver repositórios marcados para outros
  países; a Metragen só atende condomínios brasileiros, então a chave evita
  ruído nas lojas dos demais países. É ela também que define o pt-BR como
  idioma do repositório (veja "Idioma").
- Os assets da marca ficam em `custom_components/<domain>/brand/` — `icon.png`,
  `icon.svg`; nenhum `logo.png` é distribuído porque o Home Assistant recai no
  ícone para ele. O Home Assistant 2026.3+ serve o diretório direto da
  integração, antes do CDN do
  [home-assistant/brands](https://github.com/home-assistant/brands), então não
  é preciso submeter nada ao brands; o `brand/README.md` registra a origem e as
  regras de tamanho.
- Um `README.md` na raiz do repositório é obrigatório; o HACS o exibe como a
  descrição da integração. O cabeçalho dele segue o layout abaixo.

O release-please marca as releases a cada merge na `main`; o HACS exibe aos
usuários as cinco releases mais recentes do GitHub, então mantenha o changelog
fácil de buscar.

## Cabeçalho do README

Todo repositório abre o `README.md` com o mesmo cabeçalho, exatamente nesta
ordem: **título → badges → link do HACS → separador `---` → o restante do
documento.**

```markdown
# <Título>

[![CI](https://github.com/roquerodrigo/<repo>/actions/workflows/ci.yml/badge.svg)](https://github.com/roquerodrigo/<repo>/actions/workflows/ci.yml)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

[![Abra a sua instância do Home Assistant e o repositório dentro do HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=roquerodrigo&repository=<repo>&category=integration)

---
```

- `owner=` é sempre `roquerodrigo`; `repository=` é o nome do repositório.
- `category=integration` para uma integração; `category=plugin` para um
  repositório de card Lovelace.
- O link do HACS é um parágrafo próprio, separado do bloco de badges por uma
  linha em branco. A linha de badges e o botão "Abra a sua instância do Home
  Assistant" são coisas diferentes e não podem ficar juntos.
- Preserve os badges que o repositório já tem e não invente novos; todos ficam
  **antes** do link do HACS.
- O `---` logo após o link do HACS é o separador do cabeçalho. Um README que já
  usa `---` mais abaixo mantém esses como quebras de seção — não adicione um
  segundo separador ao cabeçalho.

**Repositório privado não leva link do HACS.** O `my.home-assistant.io` resolve
o destino pela API pública do GitHub, então em um repositório privado o botão
cai em algo que o HACS não consegue instalar. É o mesmo motivo pelo qual esses
repositórios chamam o workflow de validação com `hacs: false`. Publique o
título, os badges e o separador, e adicione o link quando — e somente quando —
o repositório se tornar público.

## Quality scale

- O `quality_scale.yaml` é **opcional** e este repositório não traz um. Ele só
  é exigido quando o `manifest.json` declara um nível de `quality_scale` — e,
  nesse caso, toda afirmação nele precisa ser honesta (`done` só quando a regra
  está de fato implementada; use `todo`/`exempt` caso contrário).
- O objetivo é aplicar as [regras Bronze/Silver/Gold](https://developers.home-assistant.io/docs/core/integration-quality-scale/)
  pertinentes à integração; Platinum é uma aspiração, não um gate de review.

## Hooks de pre-commit

O `pre-commit` é uma dependência de desenvolvimento (`pyproject.toml`), e o
`.pre-commit-config.yaml` roda ruff format, ruff check e mypy como **hooks
locais via `uv run`**, de modo que todo commit usa exatamente as versões das
ferramentas fixadas em `pyproject.toml`/`uv.lock` — as mesmas que o CI resolve.
Nunca troque esses hooks por espelhos (`ruff-pre-commit`, `mirrors-mypy`): um
hook espelhado carrega o próprio pin de versão, que se afasta do pin do projeto
sem avisar. Instale uma vez por clone:

```bash
pre-commit install
```

O hook roda em todo commit os mesmos gates de lint do CI. Só o pule em um
`git commit --no-verify` de emergência, e rode de novo o `scripts/lint` (ou os
comandos diretos equivalentes) logo em seguida.

## Conventional commits

Todos os commits seguem o [Conventional Commits](https://www.conventionalcommits.org/),
que o `release-please` interpreta para subir a versão e gerar o `CHANGELOG.md`:

| Tipo | Significado | Bump |
|---|---|---|
| `feat` | Nova funcionalidade | minor |
| `fix` | Correção de bug | patch |
| `perf` | Melhoria de desempenho | patch |
| `deps` | Atualização de dependência | patch |
| `docs` | Apenas documentação | nenhum |
| `refactor` | Refatoração sem mudança de comportamento | nenhum |
| `test` | Mudança só em testes | nenhum |
| `ci` | Mudança de CI / ferramental | nenhum |
| `chore` | Qualquer outra coisa (raro) | nenhum |

- Assunto: em pt-BR, no imperativo, em minúsculas, sem ponto final. O tipo e o
  escopo ficam sempre em inglês.
- Use escopos quando ajudar:
  `fix(sensor): mapeia valores fora do enum para None`.
- Um rodapé `BREAKING CHANGE:` (ou `!` após o tipo) sobe a versão major.

## Lint e verificação

- A configuração do Ruff fica no `pyproject.toml` (`[tool.ruff]`), com
  `select = ["ALL"]`.
- A configuração do mypy fica no `pyproject.toml` (`[tool.mypy]`). Rode os dois
  com `uv run ruff check .` e `uv run mypy custom_components/metragen`.
- Após cada mudança, rode `uv run ruff format --check .`, `uv run ruff check .`,
  `uv run mypy custom_components/metragen` e `uv run pytest`. Os dois gates
  espelham o CI. O `scripts/lint` é um wrapper fino que só encadeia esses
  quatro comandos — rodá-lo ou rodar os comandos diretamente é equivalente; o
  wrapper existe para que o CI, a documentação e o hábito local tenham uma
  única fonte da verdade.
- Os testes ficam em `tests/`, espelhando o layout de produção. O gate de 90 %
  de cobertura (`pyproject.toml`, `[tool.pytest.ini_options]`) impede que
  código sem teste entre despercebido. Quando um teste exercita um estado
  impossível sob os novos tipos, atualize-o ou remova-o — nunca enfraqueça o
  tipo para satisfazer o teste.
