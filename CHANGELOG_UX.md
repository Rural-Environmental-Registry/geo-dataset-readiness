# Changelog - Melhorias de UX/UI

## Versão 1.1 - Melhorias de Usabilidade

### 🎯 Objetivo
Melhorar a experiência do usuário (UX) seguindo melhores práticas de design de interface, tornando a estrutura da tela previsível e consistente desde o primeiro momento.

### ✨ Mudanças Implementadas

#### 1. **Seção de Mapeamento Sempre Visível**
- **Antes**: A seção de mapeamento de camadas só aparecia após selecionar um arquivo
- **Depois**: A seção está sempre visível desde a abertura do plugin
- **Benefício**: O usuário compreende a estrutura completa da interface antes de qualquer ação

#### 2. **Tabela com Placeholder**
- **Implementação**: Tabela pré-populada com as 10 camadas esperadas mostrando "—" na coluna "Encontrada"
- **Cores**: Texto em cinza secundário (`GovBRTokens.TEXT_SECONDARY`) para indicar estado inativo
- **Benefício**: Usuário já visualiza quais camadas o sistema espera encontrar

#### 3. **Resumo Estatístico Inicial**
- **Texto inicial**: "10 esperadas · 0 identificadas · 0 precisam de associação"
- **Estilo inicial**: Cor secundária indicando estado inativo
- **Após seleção**: Cor primária e negrito quando dados reais são carregados
- **Benefício**: Feedback visual claro sobre o estado da interface

#### 4. **Linha Separadora**
- **Localização**: Entre a seção de mapeamento e os controles de validação
- **Estilo**: `QFrame` com `objectName="divider"` usando cor `GovBRTokens.DIVIDER`
- **Benefício**: Separação visual clara entre seções funcionais da interface

#### 5. **Dimensões Otimizadas**
- **Tabela**:
  - Altura mínima: 180px
  - Altura máxima: 220px
  - Largura das colunas ajustada para melhor visualização
- **Dialog**:
  - Tamanho mínimo aumentado de 960×680 para 1000×720
  - Acomoda todos os elementos sem scroll na maioria dos casos

#### 6. **Função de Reset**
- Nova função `_reset_mapping_table()` para retornar ao estado placeholder
- Limpa mapeamentos e renomeações pendentes
- Restaura cores e textos para estado inativo

### 📐 Design Tokens GOV.BR DS Utilizados

```python
GovBRTokens.TEXT_PRIMARY     # Texto ativo (dados carregados)
GovBRTokens.TEXT_SECONDARY   # Texto placeholder (estado inicial)
GovBRTokens.SUCCESS          # ✓ Coincidente (verde)
GovBRTokens.ERROR            # ✗ Não encontrada (vermelho)
GovBRTokens.WARNING          # ⚠ Renomear (amarelo)
GovBRTokens.DIVIDER          # Linha separadora (#E6E6E6)
```

### 🎨 Comportamento Visual

1. **Ao abrir o plugin**:
   - Tabela visível com placeholder
   - Resumo mostra "0 identificadas"
   - Botão "Renomear Camadas" desabilitado
   - Cores em cinza secundário

2. **Ao selecionar arquivo**:
   - Tabela atualiza com dados reais
   - Cores mudam para estados ativos (verde/vermelho/amarelo)
   - Resumo atualiza com números reais em negrito
   - ComboBoxes aparecem para camadas não encontradas

3. **Ao fazer associações**:
   - Situação muda para "⚠ Renomear" (amarelo)
   - Botão "Renomear Camadas" habilita
   - Outras ComboBoxes removem a opção já selecionada

### 🔄 Fluxo de Estados

```
Estado Inicial (Placeholder)
    ↓ [Selecionar arquivo]
Estado Carregado (Dados reais)
    ↓ [Fazer associação]
Estado Pendente (Com renomeações)
    ↓ [Clicar "Renomear Camadas"]
Estado Carregado (Atualizado)
```

### ✅ Benefícios de Usabilidade

1. **Previsibilidade**: Usuário vê a estrutura completa desde o início
2. **Feedback Imediato**: Estados visuais claros (inativo vs ativo)
3. **Orientação**: Layout guia o fluxo de trabalho naturalmente
4. **Consistência**: Elementos não "pulam" ou aparecem inesperadamente
5. **Clareza**: Separação visual entre seções funcionais
6. **Acessibilidade**: Cores seguem padrão GOV.BR DS com bom contraste

### 📝 Notas de Implementação

- Mantida compatibilidade total com funcionalidades existentes
- Sem alterações na lógica de negócio ou validação
- Apenas mudanças de apresentação visual e timing de exibição
- Código segue as mesmas convenções e padrões do projeto
