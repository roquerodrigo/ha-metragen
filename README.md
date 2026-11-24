# Metragen

<!-- ha-marketplace:exclude-start -->
[![CI](https://github.com/roquerodrigo/ha-metragen/actions/workflows/ci.yml/badge.svg)](https://github.com/roquerodrigo/ha-metragen/actions/workflows/ci.yml)
[![GitHub release](https://img.shields.io/github/v/release/roquerodrigo/ha-metragen)](https://github.com/roquerodrigo/ha-metragen/releases/latest)
[![Sponsor](https://img.shields.io/badge/Sponsor-%E2%9D%A4-db61a2?logo=githubsponsors&logoColor=white)](https://github.com/sponsors/roquerodrigo)

[![Abra a sua instância do Home Assistant e o repositório no Marketplace.](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=roquerodrigo&repository=ha-metragen&category=integration)
<!-- ha-marketplace:exclude-end -->

Acompanhe no Home Assistant o consumo de água e gás do seu apartamento, em
condomínios com medição individualizada da
[Metragen](https://www.sistemametragen.com.br/metragen). Você entra com o
mesmo login do Portal do Morador e vê a leitura, o consumo e o valor cobrado
de cada medidor. O histórico mês a mês que o portal guarda vai para o painel
de Energia.

## Recursos

- Veja a última leitura, o consumo do mês e o valor cobrado de cada medidor
  de água fria, água quente e gás.
- Acompanhe quanto você já consumiu no ano.
- Coloque a água e o gás no painel de Energia, com o custo de cada mês e o
  histórico dos anos anteriores trazido do portal.
- Medidores novos que aparecem no portal entram no Home Assistant sem
  reiniciar.

## Requisitos

- Home Assistant 2026.7.2 ou mais recente.
- Um apartamento em condomínio atendido pela Metragen, com cadastro no Portal
  do Morador (formulário **Registre-se** do portal).
- Acesso do Home Assistant à internet. Os dados vêm do site da Metragen.

<!-- ha-marketplace:exclude-start -->
## Instalação

### Marketplace do Home Assistant (recomendado)

1. Selecione o botão **Abra a sua instância do Home Assistant** acima, ou vá
   em **Configurações → Marketplace**, selecione **Adicionar a partir de
   link** no canto superior direito, informe `roquerodrigo/ha-metragen` no
   campo **Link do GitHub** e selecione **Adicionar**.
2. Selecione **Instalar**.
3. Reinicie o Home Assistant.

O Marketplace vem com o Home Assistant 2026.11 e posteriores. Em versões
anteriores, adicione este repositório ao HACS como repositório personalizado
do tipo **Integração** e instale por lá.

### Manual

1. Baixe o `metragen.zip` da
   [última versão](https://github.com/roquerodrigo/ha-metragen/releases/latest).
2. Extraia o conteúdo em `config/custom_components/metragen/`.
3. Reinicie o Home Assistant.
<!-- ha-marketplace:exclude-end -->

## Configuração

Vá em **Configurações → Dispositivos e serviços → Adicionar integração**,
procure **Metragen** e preencha o formulário.

| Campo            | O que informar                                             |
|------------------|------------------------------------------------------------|
| Código ou e-mail | O código ou o e-mail que você cadastrou no Portal do Morador |
| Senha            | A senha do Portal do Morador                               |

Use o login de morador, e não o da administração do condomínio. Para
acompanhar outro apartamento, adicione a integração de novo com a conta dele.

Para trocar a senha depois, abra a integração e selecione **Reconfigurar**.
O código ou e-mail precisa ser o mesmo usado na configuração. Se o portal
deixar de aceitar a senha, o Home Assistant pede as credenciais novas.

## Opções

Abra a integração e selecione **Configurar**.

| Opção                            | Padrão            | Valores        | Efeito                                      |
|----------------------------------|-------------------|----------------|---------------------------------------------|
| Intervalo de consulta (segundos) | 3600 (uma hora)   | 300 ou mais    | De quanto em quanto tempo o portal é consultado |

O portal publica uma leitura por mês, então consultar com mais frequência não
traz ganho perceptível.

## Entidades

Cada medidor que o portal lista vira um dispositivo, com o código do medidor e
o que ele mede no nome: AF1234 Água Fria, AQ1234 Água Quente, AQ1234 Gás. Um
código que não começa com AF ou AQ aparece como Água (por exemplo, AB1234
Água).

Em condomínios que cobram o aquecimento da água pelo gás, o medidor de água
quente aparece duas vezes: como Água Quente, com a conta de água, e como Gás,
com a cobrança do aquecimento.

### Cada medidor

| Entidade       | Tipo   | Unidade | Mostra                                                 |
|----------------|--------|---------|--------------------------------------------------------|
| Leitura        | Sensor | m³      | O valor do contador na última leitura publicada        |
| Consumo Mensal | Sensor | m³      | O volume cobrado no mês da última leitura              |
| Custo Mensal   | Sensor | BRL     | O valor cobrado por esse medidor no mês da última leitura |
| Consumo Anual  | Sensor | m³      | O volume somado desde a primeira leitura do ano        |

Todos os sensores trazem os atributos `meter_code`, `year` e `month`, que
dizem a qual medidor e a qual mês de cobrança o valor se refere.

### Histórico e painel de Energia

Os sensores mostram só a última leitura. O histórico mês a mês que o portal
guarda vai para as estatísticas de longo prazo do Home Assistant, em duas
séries por medidor:

| Estatística                     | Unidade | Guarda                       |
|---------------------------------|---------|------------------------------|
| `metragen:<código>_<tipo>`      | m³      | O consumo de cada mês        |
| `metragen:<código>_<tipo>_cost` | BRL     | O valor cobrado em cada mês  |

`<código>` é o código do medidor em minúsculas e `<tipo>` é `water` ou `gas`,
por exemplo `metragen:af1234_water` e `metragen:aq1234_gas`. A série de
consumo tem o nome do dispositivo (AF1234 Água Fria) e a de custo acrescenta
Custo Mensal (AF1234 Água Fria Custo Mensal). Os nomes seguem o idioma do
Home Assistant. O valor de cada mês fica no primeiro dia daquele mês.

Para usar as séries no painel de Energia:

1. Vá em **Configurações → Energia**.
2. Em **Consumo de água**, selecione **Adicionar fonte de água** e escolha a
   série de consumo do medidor, como AF1234 Água Fria. Para o gás, use
   **Adicionar fonte de gás** em **Consumo de gás**.
3. Para acompanhar o custo, selecione **Usar uma entidade que rastreie os
   custos totais** e escolha a série de custo do mesmo medidor, como AF1234
   Água Fria Custo Mensal.

Use as séries, e não o sensor Leitura, como fonte do painel. As séries
colocam o consumo de cada mês no mês certo e já trazem o histórico. O sensor
Leitura conta o mês inteiro no momento em que a leitura nova chega. Não
cadastre os dois para o mesmo medidor, senão o consumo aparece em dobro.

Você também pode ver qualquer uma das séries num card de gráfico de
estatísticas.

## Como funciona

A Metragen não oferece uma API pública. A integração lê o mesmo Portal do
Morador que você abre no navegador, com o seu login, e busca as leituras de
água e gás a cada hora (ajustável em Opções). Como o portal publica uma
leitura por mês, os valores mudam uma vez por mês.

Na primeira atualização, a integração volta ano a ano no portal, até 10 anos
antes do atual, e importa todos os meses que encontrar. Depois disso, ela só
acrescenta os meses novos.

No começo do ano, enquanto o portal ainda não tem leituras do ano corrente, os
sensores continuam mostrando a última leitura do ano anterior.

Se o portal sair do ar, os sensores mantêm os últimos valores por até 24 horas
antes de ficarem indisponíveis.

## Solução de problemas

**O formulário diz que o portal rejeitou o código/e-mail ou a senha.** A
integração usa o login do Portal do Morador, criado no formulário
**Registre-se** do portal, e não o da administração do condomínio. Confira se
o login funciona no site.

**O Home Assistant pede para autenticar de novo.** A senha mudou ou o portal
deixou de aceitá-la. Informe as credenciais atuais no aviso de
reautenticação em **Configurações → Dispositivos e serviços**.

**Os valores não mudaram este mês.** O portal publica as leituras uma vez por
mês. Os atributos `year` e `month` dos sensores mostram a qual mês o valor
atual se refere.

**As entidades ficaram indisponíveis.** O portal está fora do ar há mais de 24
horas ou deixou de listar o medidor. Um medidor que o portal não lista mais
pode ser excluído na página do dispositivo.

**O consumo aparece em dobro no painel de Energia.** O sensor Leitura e a
série do mesmo medidor estão cadastrados como fonte. Remova o sensor e mantenha
a série.

**Outro problema.** Na página da integração, selecione **Habilitar log de
depuração**, reproduza o problema e selecione **Desabilitar log de depuração**
para baixar o log. Abra uma
[issue](https://github.com/roquerodrigo/ha-metragen/issues) com o log e o
arquivo de **Fazer download dos diagnósticos**. O login, a senha e os códigos
dos medidores são removidos desse arquivo.

## Limitações conhecidas

- O portal informa uma leitura por mês. Não há consumo diário nem por hora.
- Um mês que o portal corrigir depois de importado não muda no histórico.
- O histórico importado cobre o ano atual e os 10 anteriores, no máximo.
- Remover a integração mantém as estatísticas. Para apagá-las, use a aba
  **Estatísticas** em **Configurações → Ferramentas**.

## Apoie o projeto

Esta integração é desenvolvida e mantida no meu tempo livre. Se ela for útil
para você, considere
[patrocinar o trabalho](https://github.com/sponsors/roquerodrigo). É o que
garante as correções, os testes e as novas versões.

Para relatar um bug ou pedir uma melhoria, abra uma
[issue](https://github.com/roquerodrigo/ha-metragen/issues).

<!-- ha-marketplace:exclude-start -->
## Contribuindo

Veja o [CONTRIBUTING.md](CONTRIBUTING.md) para o ambiente de desenvolvimento e
o fluxo de trabalho, e o [CODE_STYLE.md](CODE_STYLE.md) para as convenções de
código.

## Licença

[MIT](LICENSE)
<!-- ha-marketplace:exclude-end -->
