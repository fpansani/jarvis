# Jarvis

Assistente de voz em Python que executa tarefas no computador. Você aperta um atalho, fala um comando em português e o Jarvis entende o que você quer, responde e usa o PyAutoGUI para controlar o mouse e o teclado e fazer a tarefa: abrir programas, criar documentos, fazer contas, abrir sites, dizer a hora e a temperatura.

## Funcionalidades

- Reconhecimento de voz em português, com o Google (online) e o Vosk (offline, sem internet)
- Ativação pelo teclado (**CTRL+ALT+J**), com qualquer janela na frente, e cancelamento pelo mesmo atalho
- Frases prontas em **CTRL+ALT+NUM 0-9**, para apresentações sem depender do microfone
- Comandos em linguagem natural: palavras-chave sem acento e sem maiúsculas
- Automação da área de trabalho: Calculadora, Word, Excel, Paint e sites no Edge
- Hora atual e temperatura de qualquer cidade (Open-Meteo)
- Modo de depuração com horários, títulos de janela, tempos e erros detalhados, também em arquivo
- Fácil de estender: um comando novo é uma palavra-chave e uma função

## Tecnologias

- **Python 3.13.0**
- **SpeechRecognition**: transforma a voz em texto (Google, online)
- **Vosk**: reconhecimento de voz offline, usado quando não há internet
- **PyAudio**: acesso ao microfone
- **pynput**: atalhos globais de teclado (CTRL+ALT+J e CTRL+ALT+NUM 0-9)
- **PyAutoGUI**: controla o mouse e o teclado
- **Requests**: consulta da temperatura (API Open-Meteo)
- **Pillow** e **OpenCV**: reconhecimento de imagens na tela (usado pelo PyAutoGUI)

## Requisitos

- **Windows 10** (o projeto foi feito para rodar só no Windows)
- **Python 3.13.0** (veja a observação abaixo)
- Um microfone funcionando
- Internet para o melhor reconhecimento de voz, para a temperatura e para os sites. Sem internet, o Jarvis usa o reconhecimento offline (veja [Modo offline](#modo-offline)).

> **Observação:** o Python 3.14 não é suportado. Use o 3.13.0 para que todos os pacotes instalem corretamente, principalmente o PyAudio, que precisa de um pacote pronto para a sua versão do Python no Windows.
>
> Se você tem mais de uma versão do Python instalada, rode `py -0` para listá-las e use `py -3.13` para escolher a certa.

## Instalação

### 1. Baixe o projeto

```bash
git clone https://github.com/marcospmtech/jarvis
cd jarvis
```

### 2. Crie o ambiente virtual (`.venv`) com o Python 3.13

```powershell
py -3.13 -m venv .venv
```

### 3. Ative o ambiente virtual

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Prompt de Comando (CMD):

```bat
.venv\Scripts\activate.bat
```

Com o ambiente ativo, o prompt começa com `(.venv)`. Confira a versão:

```powershell
python --version
```

Deve aparecer `Python 3.13.0`.

### 4. Instale as dependências

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 5. (Opcional) Baixe um modelo para o modo offline

Veja [Modo offline](#modo-offline). Sem o modelo, o Jarvis funciona normalmente com internet.

## Como usar

Com o ambiente virtual ativo:

```powershell
python main.py
```

Na abertura, o Jarvis confere o microfone, a internet e o modelo offline, e mede o ruído do ambiente (fique em silêncio nesse segundo). Depois aparece:

```
Olá, usuário. No que posso ajudar hoje?
Pressione CTRL+ALT+J para falar.
```

Aperte **CTRL+ALT+J**, espere o bipe e fale o comando. O Jarvis mostra o que entendeu, responde, espera 2 segundos e executa a tarefa:

```
> Jarvis, abra o Paint.
Certo, irei abrir o Paint.
A tarefa foi executada com sucesso.
--
Pressione CTRL+ALT+J para falar.
```

Para sair, aperte **CTRL+C** na janela do Jarvis.

### Ativação pelo teclado (CTRL+ALT+J)

- O Jarvis só ouve depois do **CTRL+ALT+J**. O atalho funciona com qualquer janela na frente, até o Word ou o Edge que ele mesmo abriu.
- Se você não falar nada em 10 segundos, aparece `(não entendi)` e ele volta a esperar o atalho.
- **Cancelar:** aperte **CTRL+ALT+J de novo enquanto o Jarvis ouve**. Ele para na hora, toca um bipe mais grave, mostra `(cancelado)` e volta a esperar. Se a frase já estiver sendo reconhecida, o resultado é descartado e nada é executado.
- Atalhos apertados enquanto o Jarvis está ocupado (ouvindo ou executando uma tarefa) são ignorados, então um aperto duplo não dispara um segundo comando.
- As teclas que o próprio Jarvis aperta pelo PyAutoGUI nunca disparam os atalhos.
- O CTRL+ALT+J também chega à janela da frente. Nos programas que o Jarvis usa ele não faz nada, mas lembre disso se trocar o atalho.

### Frases prontas (CTRL+ALT+NUM 0-9)

Para apresentações, **CTRL+ALT + um número do teclado numérico** faz o Jarvis agir como se você tivesse falado uma frase fixa. Depois de uma pausa curta, a frase aparece depois do `> `, igual a uma fala reconhecida, e segue o mesmo caminho dos comandos de voz. O microfone não é usado.

| Atalho | Frase | Precisa de internet |
|---|---|---|
| CTRL+ALT+NUM 1 | "Jarvis, que horas são?" | Não |
| CTRL+ALT+NUM 2 | "Jarvis, qual a temperatura em Santo André?" | Sim |
| CTRL+ALT+NUM 3 | "Jarvis, calcule 5 vezes 2." (só responde; não abre a Calculadora) | Não |
| CTRL+ALT+NUM 4 | "Jarvis, crie um novo documento no Word e escreva uma saudação." | Não |
| CTRL+ALT+NUM 5 | "Jarvis, crie uma nova planilha no Excel." | Não |
| CTRL+ALT+NUM 6 | "Jarvis, abra o Paint." | Não |
| CTRL+ALT+NUM 7 | "Jarvis, abra o YouTube." | Sim |
| CTRL+ALT+NUM 8 | "Jarvis, me mostre as notícias do dia." | Sim |
| CTRL+ALT+NUM 9 | "Jarvis, abra o site do colégio." | Sim |
| CTRL+ALT+NUM 0 | "Jarvis, abra o Instagram do colégio." | Sim |

- Só valem as teclas do **teclado numérico** (com o NumLock ligado ou desligado), não os números acima das letras.
- Essas teclas são bloqueadas para a janela da frente: o Word ou o Bloco de Notas nunca recebem o número quando você usa um atalho. Sem CTRL+ALT, o teclado numérico funciona normalmente.
- **Trocar uma frase:** edite `FRASES` em `atalhos.py` (escreva como você falaria). Apague uma linha para liberar a tecla.
- **Pausa antes de a frase aparecer:** `PAUSA_ANTES_DA_FRASE` em `atalhos.py` (use `0` para mostrar na hora).
- **Testar os atalhos sem executar nada:** `python ativacao.py` mostra cada atalho detectado e a frase dele. Deixe o Bloco de Notas na frente durante o teste: nenhum número pode aparecer nele.

## Comandos

Fale naturalmente: o Jarvis procura as palavras-chave de `words.py` na frase, sem ligar para acentos e maiúsculas. Se a frase tiver palavras-chave de comandos diferentes, os nomes de programas e sites (lista `app_names` em `words.py`) vencem as palavras genéricas, e entre palavras do mesmo tipo vence a mais longa: "abra o site da CNN" abre a CNN, e "abra o site do Instagram" abre o Instagram, não o site do colégio.

| Comando | Exemplo | O que faz |
|---|---|---|
| `time` | "Que horas são?" | Diz a hora atual |
| `degree` | "Qual a temperatura em Curitiba?" | Diz a temperatura atual na cidade pedida (padrão: Santo André) |
| `calc` | "Abra a calculadora" / "Calcule 5 vezes 2" / "Faça 2 x 2" / "Faz 2 x 2 pra mim" | Abre a Calculadora ou só diz o resultado da conta. Diga "...na calculadora" ("Calcule 5 vezes 2 na calculadora") para ela também digitar a conta lá |
| `word` | "Crie um novo documento no Word e escreva uma saudação" | Abre o Word, cria um documento (crie, faça, novo...) e, se pedido, escreve uma saudação |
| `excel` | "Crie uma nova planilha no Excel" / "Faça uma planilha no Excel" | Abre o Excel e, se pedido (crie, faça, nova...), cria uma planilha em branco |
| `paint` | "Abra o Paint" | Abre o Paint |
| `yt` | "Abra o YouTube" | Abre o YouTube no Edge |
| `news` | "Me mostre as notícias do dia" | Abre a CNN Brasil no Edge |
| `site` | "Abra o site do colégio" | Abre o site do colégio no Edge |
| `insta` | "Abra o Instagram do colégio" | Abre o Instagram do colégio no Edge |

Dicas:

- **Temperatura:** a cidade pode vir antes ou depois ("Em Curitiba, qual a temperatura?", "Qual o clima na cidade de Santos agora?"). Sem cidade, vale Santo André.
- **Contas:** peça com "calcule", "calcula", "faça" ou "faz" ("faça 2 x 2", "faz 2 x 2 pra mim", "faça a conta de 10 dividido por 4"). O Jarvis soma, subtrai, multiplica e divide, com números falados ou por extenso ("dois mil e quinhentos dividido por cinco", "dois vírgula cinco vezes quatro"), e respeita a ordem das operações.
- **Word e Excel:** se um documento ou planilha seu já estiver na frente, o Jarvis espera a janela nova abrir antes de apertar Enter ou escrever, para não mexer no seu arquivo.

## Modo offline

Com internet, o Jarvis reconhece a voz pelo Google. Sem internet (ou se o Google parar de responder), ele passa para o **Vosk**, que roda no próprio computador. Para isso, é preciso um modelo do Vosk em português na pasta `models/` (ele não fica no repositório por causa do tamanho):

1. Baixe um modelo em português em <https://alphacephei.com/vosk/models>. O `vosk-model-small-pt-0.3` (31 MB) carrega rápido, mas reconhece mal; o [`vosk-model-pt-fb-v0.1.1-pruned`](https://github.com/alphacep/vosk-api/issues/991#issuecomment-1197512394) funcionou bem nos testes.
2. Descompacte dentro de `models/`, ficando por exemplo `models/vosk-model-pt-fb-v0.1.1-pruned/` (com os arquivos do modelo direto dentro).
3. Rode `python main.py` normalmente.

Como funciona:

- **Sem internet ao abrir:** o modelo é carregado na hora (alguns segundos) e o Jarvis começa no modo offline.
- **A internet cai durante o uso:** a frase que você acabou de falar é reconhecida pelo Vosk, e o Vosk continua sendo usado por 30 segundos antes de o Google ser tentado de novo. Quando a conexão volta, o Jarvis volta ao Google sozinho.
- **Com internet:** o Vosk fica descarregado (sem gastar memória) até ser preciso.
- **Vários modelos em `models/`:** o Jarvis prefere um que não seja o "small". Para escolher, defina a variável `JARVIS_MODELO_VOSK` com o nome da pasta (PowerShell: `$env:JARVIS_MODELO_VOSK = "vosk-model-pt-fb-v0.1.1-pruned"`).
- O modo offline só reconhece a voz. Os comandos que precisam de internet (temperatura e sites) continuam precisando dela.
- O Vosk escreve tudo em minúsculas e pode errar palavras estrangeiras (Excel, YouTube, Instagram). Se um comando não for detectado offline, veja como o Jarvis escreveu o que você disse e acrescente essa grafia em `words.py`.

## Depuração

Por padrão, o Jarvis mostra só o que você disse, as respostas e, quando algo falha, o motivo. Para ver o passo a passo, há duas opções, que podem ser usadas juntas:

| Opção | Onde | O que faz |
|---|---|---|
| `DEBUG = True` | `automacao/comum.py` | Mostra no console as linhas `[debug 14:03:22.123] ...` e o cabeçalho `** MODO DEBUG **` |
| `SALVAR_LOG = True` | `automacao/comum.py` | Grava as mesmas mensagens (e os erros) em `jarvis.log`, na pasta do projeto, mesmo com o debug desligado |

O debug mostra:

- **Ambiente:** versões do Python, do Windows e dos pacotes, e o microfone usado.
- **Reconhecimento:** duração do áudio, se usou Google ou Vosk, quanto tempo levou e por que o Google falhou.
- **Comando:** qual comando foi detectado e por qual palavra-chave (e quais disputaram).
- **Contas e temperatura:** como a conta foi interpretada e como a cidade foi encontrada.
- **Janelas:** cada título de janela visto enquanto o Jarvis espera um programa abrir. É o mais útil quando uma automação falha.
- **Ações:** quanto tempo cada ação levou e se deu certo.
- **Erros inesperados:** o traceback completo, em vez da mensagem curta.

O `SALVAR_LOG` é útil em apresentações: a tela fica limpa e, se algo der errado, o motivo fica registrado no `jarvis.log`.

Também dá para ligar as duas opções só por uma execução, sem mexer no código:

```powershell
$env:JARVIS_DEBUG = "1"    # PowerShell (debug no console)
$env:JARVIS_LOG = "1"      # PowerShell (log em arquivo)
python main.py
```

```bat
set JARVIS_DEBUG=1
set JARVIS_LOG=1
python main.py
```

Elas valem enquanto aquela janela do terminal estiver aberta. Para desligar, feche a janela ou use o valor `0`.

### Testar partes isoladas

Da pasta do projeto, com o `.venv` ativo:

```powershell
python ativacao.py                                          # testa os atalhos, sem executar nada
python -m automacao.calc calcule 5 vezes 2 na calculadora   # testa uma automação sozinha
python -m automacao.word crie um novo documento no word e escreva uma saudação
python -m automacao.youtube abra o youtube
```

Nas automações testadas sozinhas, a frase vem dos argumentos, e os erros também aparecem em caixas de diálogo.

## Configurações

| O que | Onde | Padrão |
|---|---|---|
| Atalho para ouvir | `ATALHO` em `ativacao.py` (formato do pynput: `"<ctrl>+<shift>+k"`, `"<f9>"`) | `"<ctrl>+<alt>+j"` |
| Ouvir o tempo todo, sem atalho (como nas versões antigas) | `ATIVACAO_POR_TECLA` em `main.py` | `True` (usa o atalho) |
| Bipe ao ouvir e ao cancelar | `BIPE_AO_OUVIR` em `main.py` | `True` |
| Terminal verde, estilo Matrix (fundo preto, letras verdes; volta ao normal ao sair) | `COR_MATRIX` em `main.py` | `True` |
| Frases prontas e pausa antes delas | `FRASES` e `PAUSA_ANTES_DA_FRASE` em `atalhos.py` | 10 frases, 1 s |
| Palavras-chave dos comandos | `words.py` | — |
| Cidade padrão da temperatura | `CIDADE_PADRAO` e `COORDENADAS_PADRAO` em `functions.py` | Santo André |
| Espera pela fala / duração máxima da frase | `ESPERA_PELA_FALA` e `DURACAO_MAXIMA_FALA` em `voice.py` | 10 s / 15 s |
| Espera entre a resposta e a ação | `ATRASO_APOS_RESPOSTA` em `automacao/comum.py` | 2 s |
| Debug e log em arquivo | `DEBUG` e `SALVAR_LOG` em `automacao/comum.py` | desligados |

Se o atalho de teclado não puder ser ativado, o Jarvis avisa no cabeçalho e passa a ouvir o tempo todo.

## Estrutura do projeto

```
jarvis/
├── main.py            # inicialização, tela e laço principal (esperar atalho -> ouvir -> executar)
├── voice.py           # microfone e reconhecimento de voz (Google online, Vosk offline)
├── ativacao.py        # atalhos globais de teclado (pynput)
├── atalhos.py         # frases prontas de CTRL+ALT+NUM 0-9
├── functions.py       # detecção do comando, hora, temperatura e ligação com as automações
├── words.py           # palavras-chave de cada comando
├── requirements.txt
├── models/            # modelos do Vosk (não vão para o Git)
└── automacao/         # automações PyAutoGUI, uma por comando
    ├── comum.py       # funções compartilhadas, depuração e o Plano (resposta + ação)
    ├── calc.py, word.py, excel.py, paint.py
    ├── youtube.py, noticias.py, site_clovis.py, instagram.py
    └── imgs/          # imagens usadas para achar botões na tela
```

### Como adicionar um comando

1. Em `words.py`, crie o comando com as palavras-chave dele (por exemplo, `"spotify": ["spotify", "música"]`).
2. Em `automacao/`, crie um arquivo com uma função `planejar(frase)` que devolve `Plano(resposta, acao)`. Use `iniciar_programa` ou `abrir_site`, de `comum.py`, e o decorador `@seguro` na ação. Veja `paint.py` (o mais simples) como modelo.
3. Em `functions.py`, importe o arquivo, crie a função do comando e acrescente-a em `COMANDOS`.

## Solução de problemas

- **"Não consegui abrir o microfone":** o microfone pode estar em uso por outro programa ou bloqueado em Configurações > Privacidade > Microfone. Permita o acesso de aplicativos da área de trabalho.
- **"Microfone não encontrado":** conecte o microfone. Se ele já está conectado, confira se o PyAudio foi instalado (`pip install -r requirements.txt`).
- **O atalho não funciona:** rode `python ativacao.py` e aperte o atalho para ver se ele é detectado. Com uma janela de programa aberto como administrador na frente, o Windows não deixa o atalho chegar ao Jarvis (a menos que ele também rode como administrador).
- **Os botões não são encontrados (Word, Edge):** o reconhecimento de imagens precisa do `Pillow` e do `opencv-python` (já estão no `requirements.txt`). Uma escala de tela diferente de 100% pode impedir que as imagens de `automacao/imgs/` sejam achadas.
- **"Não consegui carregar o modelo":** baixe e descompacte o modelo de novo. Se o caminho da pasta tem acentos (por exemplo, `Área de Trabalho`), mova o Jarvis ou o modelo para um caminho simples, como `C:\jarvis`.
- **O Google não responde numa rede com página de login (Wi-Fi da escola):** faça o login no navegador. Enquanto isso, o Jarvis usa o Vosk, se houver um modelo.
- **Uma automação falhou:** ligue o `DEBUG` (ou o `SALVAR_LOG`) e repita. As mensagens mostram em que passo parou e qual janela estava na frente.

## Observações

- O PyAutoGUI assume o mouse e o teclado durante as tarefas. Leve o mouse a um canto da tela para acionar o fail-safe e interromper a automação.
- A pasta `.venv` é local da sua máquina e não deve ir para o Git (já está no `.gitignore`, junto com `models/` e `jarvis.log`).
- Se uma automação falhar (janela que não abriu, imagem não encontrada, sem internet), o Jarvis mostra o motivo e continua funcionando.

## Melhorias futuras

- Mais comandos e aplicativos
- Ativação por palavra-chave falada (por exemplo, "Ei, Jarvis")
- Suporte a outros idiomas
