# Analisador de risco de compra de energia (EPRA)

[🇧🇷 PT-BR](README.pt-BR.md) · [🇬🇧 EN-UK](README.md) · [🇦🇹 DE-AT](README.de-AT.md)

## Resumo

O EPRA compara estratégias de compra de eletricidade para um consumidor industrial de referência de **50 GWh na Estíria**, usando preços reais do mercado austríaco day-ahead de 2021 a 2025. O caso de referência é construído, não representa uma empresa real.

No período histórico, a estratégia anual de preço fixo foi a mais barata, com custo calibrado de €30,17 milhões. Para os próximos 12 meses, a estratégia fixa anual tem o menor custo esperado simulado (€4,77 milhões); a estratégia híbrida com 70% fixo tem a menor exposição P95 (€6,44 milhões, contra €6,61 milhões). P95 significa que cerca de 5% dos custos simulados ultrapassam esse nível.

Os resultados simulados reamostram preços passados; não são previsões. O perfil de carga é construído e os preços de contrato usam o índice ÖSPI como proxy, não ofertas reais de fornecedores.

## O que o projeto demonstra

- Ingestão de preços da plataforma de transparência ENTSO-E.
- Pipeline de dados, consultas SQL/dbt e verificações de qualidade.
- Comparação de seis opções: spot, indexada ao ÖSPI, fixa anual e três combinações híbridas.
- Separação entre dados verificados, hipóteses calibradas e resultados simulados.

O [README completo em inglês](README.md) contém tabelas, gráficos, fontes, limites e arquitetura. A [síntese executiva](reports/EXEC_SUMMARY.md) apresenta a decisão para CFO e Compras. O pipeline principal e a primeira execução com dados reais foram concluídos; a atualização do Power BI Desktop ainda está pendente.

[Repositório](https://github.com/RafaelBraga-Kribitz/energy-procurement-risk-analyzer) · [Qualidade dos dados](reports/data_quality/DATA_QUALITY.md) · [Limitações](LIMITATIONS.md)
