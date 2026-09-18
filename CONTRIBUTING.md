# Diretrizes de contribuição

Contribuir com este projeto deve ser o mais fácil e transparente possível, seja para:

- Relatar um bug
- Discutir o estado atual do código
- Enviar uma correção
- Propor novas funcionalidades

As contribuições são escritas em português do Brasil: issues, comentários, mensagens de commit e descrições de PR. O código permanece em inglês — veja a seção "Idioma" do [`CODE_STYLE.md`](./CODE_STYLE.md).

## O GitHub é usado para tudo

O GitHub hospeda o código, acompanha issues e pedidos de funcionalidade e recebe os pull requests.

Pull requests são a melhor forma de propor mudanças no código.

1. Faça um fork do repositório e crie a sua branch a partir da `main`.
2. Se você mudou algo, atualize a documentação.
3. Garanta que o código passa no lint (rode `uv run ruff format --check .`, `uv run ruff check .` e `uv run mypy custom_components/metragen`).
4. Teste a sua contribuição.
5. Abra o pull request!

## Toda contribuição fica sob a licença MIT

Em resumo: ao enviar mudanças de código, entende-se que elas ficam sob a mesma [licença MIT](http://choosealicense.com/licenses/mit/) que cobre o projeto. Fale com os mantenedores se isso for um problema.

## Relate bugs pelas [issues](../../issues) do GitHub

As issues do GitHub são usadas para acompanhar os bugs públicos.
Relate um bug [abrindo uma nova issue](../../issues/new/choose); é simples assim!

## Escreva relatos de bug com detalhes, contexto e código de exemplo

**Bons relatos de bug** costumam ter:

- Um resumo rápido e/ou o contexto
- Passos para reproduzir
  - Seja específico!
  - Inclua código de exemplo, se puder.
- O que você esperava que acontecesse
- O que acontece de fato
- Observações (incluindo, se for o caso, por que você acha que isso acontece ou o que você tentou e não funcionou)

## Use um estilo de código consistente

O projeto usa o [ruff](https://docs.astral.sh/ruff/) (configurado no `pyproject.toml`). Rode `uv run ruff format --check .`, `uv run ruff check .` e `uv run mypy custom_components/metragen` antes de enviar um PR.

## Teste a sua modificação

Este projeto é baseado no [ha-integration-blueprint](https://github.com/roquerodrigo/ha-integration-blueprint).

Rode `scripts/setup` uma vez para criar o ambiente virtual gerenciado pelo `uv` e, depois, `scripts/develop` para iniciar uma instância independente do Home Assistant em modo debug, com a integração carregada e o arquivo [`configuration.yaml`](./config/configuration.yaml) incluído.

## Licença

Ao contribuir, você concorda que as suas contribuições serão licenciadas sob a licença MIT do projeto.
