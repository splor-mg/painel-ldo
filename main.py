from databases import carrega_trata_dados, cria_base_fonte_analise, cria_base_receita_analise

   
valor_painel = carrega_trata_dados()

cria_base_receita_analise(valor_painel=valor_painel)

cria_base_fonte_analise(valor_painel=valor_painel)
