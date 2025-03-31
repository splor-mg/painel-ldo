# CARREGAR PACOTES
library(relatorios)
library(data.table)
library(tidyverse)
library(openxlsx)
library(readxl)
library(matrixStats)
library(this.path)


# CONFIGURACOES
setwd(this.path::this.dir())
ANO_REF <- year(Sys.Date())
ANO_REF_LDO <- substr(ANO_REF+1,3,4)
DATA <- Sys.Date()
OPERADOR <- "Rodolfo"


# PARAMETROS
fontes_convenios <- c(1:9,16,17,24,36,37,56,57,62:70,73,74,92,93,97,98)


# BASE EXECUCAO
exec_rec <- filter(execucao::exec_rec, ANO >= ANO_REF - 3)
  exec_rec$VL_REC <- exec_rec$VL_EFET_AJUST
  exec_rec$UO_COD <- if_else(exec_rec$UO_COD == 9999, 9901, exec_rec$UO_COD)
  exec_rec <- add_de_para_receita(exec_rec)
  exec_rec$RECEITA_COD <- if_else(exec_rec$ANO>=2023 | is.na(exec_rec$RECEITA_COD_2), as.character(exec_rec$RECEITA_COD), as.character(exec_rec$RECEITA_COD_2))


# BASE LDO
ldo_sisor <- read_excel(paste("../!bases/sisor/BASE_ORCAM_RECEITA_FISCAL_",DATA,".xlsx", sep="")) #Salve o arquivo da LDO com formato xlsx, inserindo a data no nome do arquivo
  ldo_sisor$VL_REC <- ldo_sisor$`VALOR FINAL (R$)`
  ldo_sisor$RECEITA_COD <- ldo_sisor$COD_RECEITA
  ldo_sisor$FONTE_COD <- ldo_sisor$COD_FONTE
  ldo_sisor$RECEITA_COD <- as.character(ldo_sisor$RECEITA_COD)

ldo_rec <- read_excel("../!bases/ldo_rec.xlsx") 
  ldo_rec$RECEITA_COD <- as.character(ldo_rec$RECEITA_COD)


# BASE LOA
loa <- filter(execucao::loa_rec, ANO == ANO_REF)
  loa$VL_REC <- loa$VL_LOA_REC


# BASE RECEITA
base_rec <- bind_rows(exec_rec, loa, ldo_sisor)


# TRATAMENTO DAS BASES


# BASE CONVENIOS
base_convenios <- filter(base_rec, FONTE_COD %in% fontes_convenios)
base_convenios <- base_convenios %>% 
                  group_by(ANO, UO_COD, FONTE_COD) %>% 
                  summarise(VL_REC = sum(VL_REC))


# BASE DEMAIS FONTES
base_demais <- filter(base_rec, !FONTE_COD %in% fontes_convenios)
base_demais <- base_demais %>% 
               group_by(ANO, UO_COD, RECEITA_COD, FONTE_COD, ) %>%
               summarise(VL_REC = sum(VL_REC))
# BASE ANALISE
base_analise <- full_join(base_convenios, base_demais)

base_analise$RECEITA_COD <- if_else(is.na(base_analise$RECEITA_COD), "-", base_analise$RECEITA_COD)

base_analise <- select(base_analise, ANO, UO_COD, RECEITA_COD, FONTE_COD, VL_REC)

base_analise <- spread(base_analise, ANO, VL_REC)

base_analise[,4] <- round(if_else(is.na(as_vector(base_analise[,4])), 0, as_vector(base_analise[,4])),2) # Primeiro ano executado
base_analise[,5] <- round(if_else(is.na(as_vector(base_analise[,5])), 0, as_vector(base_analise[,5])),2) # Segundo ano executado
base_analise[,6] <- round(if_else(is.na(as_vector(base_analise[,6])), 0, as_vector(base_analise[,6])),2) # Terceiro ano executado
base_analise[,7] <- round(if_else(is.na(as_vector(base_analise[,7])), 0, as_vector(base_analise[,7])),2) # LOA ano corrente
base_analise[,8] <- round(if_else(is.na(as_vector(base_analise[,8])), 0, as_vector(base_analise[,8])),2) # LDO estimada


# ALERTAS
 base_analise$ANO <- ANO_REF
 base_analise$INTRA_SAUDE <- is_intra_saude_rec(base_analise)
 base_analise$CONVENIOS <- is_convenios_rec(base_analise)


 base_analise$ALERTAS <- if_else(base_analise$INTRA_SAUDE == TRUE,
                                           "Receita de repasse do FES é lançada pela SPLOR",
                      if_else(base_analise$FONTE_COD %in% fontes_convenios,
                                           "Receita a ser informada pela DCGCE/SEPLAG",
                      if_else(base_analise$CONVENIOS == TRUE & !base_analise$FONTE_COD %in% fontes_convenios,
                                      "RECEITA DE CONVENIOS EM FONTE NAO ESPERADA",
                      # Execucao maior que zero nos últimos 3 anos e estimativa igual a zero
                      if_else(base_analise[,4] > 0
                              & base_analise[,5] > 0
                              & base_analise[,6] > 0
                              & base_analise[,8] ==0, 
                                           "RECEITA NAO ESTIMADA", 
                      # Execucao em algum dos 2 últimos anos e estimativa igual a zero
                      if_else(base_analise[,5] > 0
                              & base_analise[,8] ==0
                              | base_analise[,6] > 0
                              & base_analise[,8] ==0,
                                            "ATENCAO", 
                      if_else(base_analise[,8] > 0
                              & (base_analise[,4] + base_analise[,5] + base_analise[,6])/3 > 0
                              & base_analise[,8] > (((base_analise[,4] + base_analise[,5] + base_analise[,6])/3)*2)
                              & base_analise[,8] > 1.2*rowMaxs(as.matrix(base_analise[,4:6]))
                              | base_analise[,8] > 0
                                 & (base_analise[,4] + base_analise[,5] + base_analise[,6])/3 > 0 
                                 & base_analise[,8] < (base_analise[,4] + base_analise[,5] + base_analise[,6])/3/2
                                 & base_analise[,8] < 0.9*rowMins(as.matrix(base_analise[,4:6])),
                                            "VALOR DISCREPANTE", 
                    "OK"))))))

  base_analise <- adiciona_desc(base_analise, c("RECEITA_COD","UO_COD"),overwrite = TRUE)
  base_analise <- select(base_analise,-ANO, -INTRA_SAUDE, -CONVENIOS)
  base_analise <- filter(base_analise, UO_COD != 4461, FONTE_COD!=58)