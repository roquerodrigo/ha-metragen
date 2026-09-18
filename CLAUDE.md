# CLAUDE.md

Orientações para agentes do Claude Code (claude.ai/code) que trabalham neste repositório.

## Sempre leia o `CODE_STYLE.md` primeiro

Antes de criar, renomear ou reestruturar qualquer arquivo/classe/função, **leia o [`CODE_STYLE.md`](./CODE_STYLE.md)**. Ele é a única fonte da verdade para as convenções: idioma, organização de arquivos, nomenclatura, tipagem, properties vs `__init__`, imports, docstrings, comentários, padrão do coordinator, layout de reparos/diagnóstico, traduções, fluxo de lint.

Para os assuntos voltados ao usuário (entidades, instalação, como o portal é acessado, diagrama de estrutura, comandos úteis, lista de CI), veja o [`README.md`](./README.md).

Este arquivo evita, de propósito, repetir essas regras — ele só acrescenta:

1. O fluxo de verificação que os agentes devem rodar após cada mudança.
2. O raciocínio de arquitetura que não fica óbvio só pelo `CODE_STYLE.md`.

## Idioma

O `hacs.json` declara `"country": ["BR"]`, então o pt-BR é o idioma deste repositório: documentação, docstrings, comentários, mensagens de commit, títulos e descrições de PR, changelog e toda comunicação pública. O código continua em inglês — identificadores, nomes de branch, mensagens de log e o tipo/escopo do Conventional Commit —, e os termos nativos do portal (`Medidor`, `Leitura`, `AreaMorador`, `FiltroAno`) nunca são traduzidos. Os detalhes estão na seção "Idioma" do `CODE_STYLE.md`.

## Origem

Este repositório foi gerado a partir do [`ha-integration-blueprint`](https://github.com/roquerodrigo/ha-integration-blueprint). A cópia foi única e unidirecional: convenções, CI e ferramental evoluem aqui de forma independente, e mudanças do blueprint só chegam se alguém as portar à mão.

## Fluxo de verificação

**Após cada mudança de código, rode sempre o lint e depois os testes, nessa ordem, antes de dar a tarefa por concluída. Rode o `scripts/lint` (um wrapper fino que só encadeia os quatro comandos) ou rode-os diretamente:**

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy custom_components/metragen
uv run pytest
```

- O lint roda `ruff format`, `ruff check` e `mypy` — todos configurados no `pyproject.toml`. Corrija qualquer falha e rode de novo antes de seguir.
- O `pytest` impõe um **gate de 90 % de cobertura** (`--cov-fail-under` no `pyproject.toml`).

Os dois gates espelham o CI (`.github/workflows/ci.yml`). Só pule isso quando a mudança literalmente não puder afetar o lint nem os testes (ex.: edições apenas no README).

## Atualizando a versão do Home Assistant

A versão do Home Assistant é fixada em dois lugares e **precisa ser atualizada em conjunto**; caso contrário, o CI, o HACS e o harness de testes se afastam:

1. `pyproject.toml`, `[dependency-groups] dev` — `homeassistant==<X.Y.Z>` (runtime/lint do CI + mypy) **e** `pytest-homeassistant-custom-component==<release correspondente>` (o harness de testes traz o próprio `homeassistant` fixado; os dois pins precisam vir da mesma release do HA, senão o lint e os testes resolvem cores diferentes).
2. `hacs.json` — `"homeassistant": "<X.Y.Z>"` (core mínimo do HA imposto pelo HACS).

Confira o pareamento no PyPI antes de commitar: o `requires_dist` do `pytest-homeassistant-custom-component` precisa listar o mesmo `homeassistant==<X.Y.Z>` que você fixou no `pyproject.toml`.

## Convenções que não ficam óbvias pelo código

A integração segue o padrão `DataUpdateCoordinator` do HA; o layout módulo a módulo está no `README.md`. Algumas escolhas não ficam evidentes lendo um único arquivo:

- O estado mora em `entry.runtime_data` (descartado automaticamente no unload), **nunca** em `hass.data`.
- O `data/__init__.py` guarda os aliases `type` (`MetragenConfigEntry`, `MetragenPayload`, `Json*`) **e** reexporta todos os símbolos dos módulos irmãos, de modo que o restante do código importa tudo de `.data`.
- O portal é um site ASP.NET MVC autenticado por cookie, sem API pública. O `api.py` é dono de todo o protocolo: o formulário de login do morador (`Portal/AcessoAoPortal`, código ou e-mail mais senha — não o formulário `UserName`/`Password` em `/metragen/`, que é o login da administração), a seleção de ano no servidor (`FiltroAno`) e a leitura dos grids Kendo. Nada acima do `api.py` sabe de HTML ou de cookies.
- O cliente autentica sob demanda. Toda leitura de grid que volta com corpo vazio levanta `MetragenApiClientAuthenticationError`; o `async_get_readings` captura isso uma vez, faz login e tenta de novo. Um segundo corpo vazio, ou um login que o portal rejeita, se propaga, e o coordinator o transforma em `ConfigEntryAuthFailed`.
- Cada config entry recebe a própria sessão `aiohttp` de `async_create_clientsession`, para que os cookies do portal nunca caiam na sessão compartilhada; o Home Assistant a desvincula quando a entry é descarregada, então a integração não deve fechá-la.
- O payload do coordinator é `Mapping[str, MetragenMeter]`, indexado por `MetragenMeter.key` (`<kind>_<código em slug>`). O medidor de água quente aparece nos dois tipos (`water_aq…` para a conta de água, `gas_aq…` para a cobrança do aquecimento) — é o que o portal informa, não um bug.
- Há um dispositivo por medidor; o nome do dispositivo vem das traduções `device.<translation_key>.name`, com o código do medidor como placeholder, escolhidas por `MetragenMeter.device_translation_key` a partir dos prefixos de código `AF`/`AQ`.
- Os medidores são descobertos dinamicamente: o `sensor/__init__.py` mantém o conjunto das chaves de medidor conhecidas e adiciona entidades para as novas a cada atualização do coordinator. Medidores que o portal deixa de listar mantêm as entidades, que ficam indisponíveis; o `async_remove_config_entry_device` permite ao usuário excluí-los.
- O histórico mensal vai para as estatísticas de longo prazo, não para entidades. O `statistics.py` (`MetragenStatisticsImporter`, executado pelo coordinator após cada atualização bem-sucedida) grava as estatísticas externas `metragen:<código em slug>_<kind>` (m³, `unit_class` volume) e `..._cost` (BRL) com `async_add_external_statistics`, nomeadas como o dispositivo do medidor pelas traduções `device` em cache (mais o nome da entidade `monthly_cost` na série de custo), para que o seletor do painel de energia leia igual à lista de dispositivos. Os ids não levam prefixo de conta de propósito: os códigos de medidor incluem o número do apartamento, e ids mais curtos foram um pedido explícito do usuário. A primeira importação volta ano a ano até o portal não retornar medidores (limite `MAX_HISTORY_YEARS`); as seguintes leem a última linha armazenada com `get_last_statistics` e só acrescentam meses mais novos, continuando o `sum` acumulado — meses revisados nunca são reescritos. Erros do portal durante a importação são logados e tentados de novo na próxima atualização; eles nunca fazem a atualização das entidades falhar. Por isso o `manifest.json` declara `recorder` em `dependencies`, e todo teste que configura uma entry precisa da fixture `recorder_mock`.
- A reautenticação está ligada para disparar quando o coordinator levanta `ConfigEntryAuthFailed`. Registre issues de Reparos (veja o helper de exemplo em `repairs.py`) a partir do coordinator/setup ao detectar um problema recuperável; as strings das issues ficam em `issues.<issue_id>` nos arquivos de tradução.
