# SICAR AD — Validar Estrutura da Base Ambiental

[![Versão](https://img.shields.io/badge/versão-0.0.1-blue)](https://github.com/Rural-Environmental-Registry/geo-dataset-readiness/releases)
[![Licença](https://img.shields.io/badge/licença-GPLv3-green)](LICENSE.txt)
[![QGIS](https://img.shields.io/badge/QGIS-3.22%2B-brightgreen)](https://qgis.org)
[![Status](https://img.shields.io/badge/status-experimental-orange)]()

> 🇺🇸 [Read in English](README.md)

Plugin QGIS para validação de consistência lógica de bases geoespaciais ambientais, alinhado à **NOTA TÉCNICA — Orientações gerais sobre as Bases de Referência para a solução da Análise Dinamizada do Cadastro Ambiental Rural (SICAR AD)** e à **ISO 19157:2013** — *Informação Geográfica — Qualidade de Dados*.

---

## Funcionalidades

Valida quatro categorias de consistência lógica definidas na ISO 19157:2013:

- **Consistência de formato** — verifica o formato do arquivo (GeoPackage ou ESRI File Geodatabase) e a legibilidade
- **Consistência conceitual** — verifica nomes de camadas, presença/ausência de atributos, contagem de registros e CRS
- **Consistência de domínio** — valida se os valores do atributo `CLASSE` estão dentro dos domínios definidos por camada
- **Consistência topológica** — detecta geometrias nulas, geometrias vazias, polígonos com área zero, erros topológicos e coordenadas 3D

Os resultados são exportados em um relatório PDF com status de conforme/divergente por regra.

---

## Requisitos

- **QGIS** 3.22 ou superior (até 4.x)
- Nenhuma dependência Python adicional necessária

---

## Instalação

1. Baixe o arquivo `.zip` da versão mais recente na página de [Releases](https://github.com/Rural-Environmental-Registry/geo-dataset-readiness/releases).
2. No QGIS, acesse **Plugins → Gerenciar e Instalar Plugins → Instalar a partir de ZIP**.
3. Selecione o arquivo `.zip` baixado e clique em **Instalar Plugin**.
4. O plugin estará disponível no menu **Plugins** como *SICAR AD — Validar Estrutura da Base Ambiental*.

> **Atenção:** Este plugin está marcado como **experimental**. Certifique-se de habilitar *Mostrar também plugins experimentais* nas configurações do gerenciador de plugins.

---

## Uso

1. Abra o QGIS e acesse o plugin em **Plugins → SICAR AD → Validar Estrutura da Base Ambiental**.
2. Na janela do plugin, selecione a base ambiental a ser validada (arquivo `.gpkg` ou pasta `.gdb`).
3. Clique em **Validar**.
4. Revise os resultados no painel do relatório de validação.
5. Opcionalmente, exporte os resultados para um arquivo CSV.

---

## Formatos aceitos

| Formato | Extensão | Tipo |
|---------|----------|------|
| GeoPackage | `.gpkg` | Arquivo |
| ESRI File Geodatabase | `.gdb` | Diretório |

---

## Regras de Validação

Para a lista completa de regras de validação, camadas esperadas, domínios de atributos e verificações topológicas, consulte [VALIDATION_RULES.md](VALIDATION_RULES.md).

---

## Referência Normativa

- **NOTA TÉCNICA** — *Orientações gerais sobre as Bases de Referência para a solução da Análise Dinamizada do Cadastro Ambiental Rural (SICAR AD)*
  - Serviço Florestal Brasileiro (SFB)
  - Validação de consistência lógica:
    - Consistência de formato
    - Consistência conceitual
    - Consistência de domínio
    - Consistência topológica
  - Baseada nos princípios da ISO 19157:2013

---

## Contribuição

Relatórios de bugs e solicitações de funcionalidades são bem-vindos via [GitHub Issues](https://github.com/Rural-Environmental-Registry/geo-dataset-readiness/issues).

Para contribuições de código, abra um pull request com uma descrição clara da mudança proposta.

---

## Licença

Este projeto está licenciado sob a **GNU General Public License v3.0**. Veja [LICENSE.txt](LICENSE.txt) para detalhes.

---

## Créditos

Desenvolvido pela **[Dataprev](https://www.dataprev.gov.br)**  
Para o **Serviço Florestal Brasileiro (SFB)** — programa SICAR AD  
Contato: sicar@dataprev.gov.br
