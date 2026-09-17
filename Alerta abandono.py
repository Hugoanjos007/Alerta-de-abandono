import math
import pandas as pd
from selenium import webdriver
import selenium
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from dotenv import load_dotenv
import os
import time
load_dotenv()
URL_TEAMS = os.getenv("url_team")
CHROME_PROFILE = os.getenv("CHROME_PROFILE")
USUARIO = os.getenv("USUARIO")
SENHA = os.getenv("SENHA")
URL_RELATORIO_1 = os.getenv("URL_RELATORIO_1")
PASTA_DOWNLOAD = os.getenv("PASTA_DOWNLOAD")
#função que cria a mensagem de alerta de abandono
def converter_numero(valor):
    if isinstance(valor, pd.Series):
        valor = valor.iloc[0]

    texto = str(valor).strip().replace("%", "")

    # Converte formato brasileiro: 1.234,56 → 1234.56
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    print(f"DEBUG — valor convertido: {texto}")
    return float(texto)


def ler_abandonos():
    rela = pd.read_csv(
        ARQUIVO_RELATORIO,
        sep=";",
        encoding="latin1"
    )
    print(f"DEBUG — abandonos lidos: {rela.loc[0, 'Abandonos']}")
    return converter_numero(rela.loc[0, "Abandonos"])


def ler_recebidas():
    rela = pd.read_csv(
        ARQUIVO_RELATORIO,
        sep=";",
        encoding="latin1"
    )
    print(f"DEBUG — recebidas lidas: {rela.loc[0, 'Recebidas']}")
    return converter_numero(rela.loc[0, "Recebidas"])


def ler_porcentagem_abandonos():
    abandonos = ler_abandonos()
    recebidas = ler_recebidas()

    if recebidas == 0:
        return 0
    print(f"DEBUG — porcentagem de abandonos calculada: {(abandonos / recebidas) * 100}")
    return (abandonos / recebidas) * 100


def calcular_porcentagens():
    abandonos = ler_abandonos()
    recebidas = ler_recebidas()

    metas = [1, 4, 6]
    faltam = []

    for meta in metas:
        total_necessario = abandonos / (meta / 100)
        faltam.append(max(0, math.ceil(total_necessario - recebidas)))
    print(f"DEBUG — faltam: {faltam}")
    return faltam
#===================================================
def alerta_abandono():
    faltam = calcular_porcentagens()

    porcentagem = ler_porcentagem_abandonos()
    recebidas = ler_recebidas()
    abandonos = ler_abandonos()

    mensagens = [
        f"📊 O abandono está em {porcentagem:.2f}%",
        f"🚨 Recebemos {recebidas:.0f} chamadas.",
        f"📴 Tivemos {abandonos:.0f} abandonos."
    ]

    if porcentagem >= 6:
        mensagens.append(f"1️⃣ Para chegar a 1% faltam {faltam[0]} chamadas.")
        mensagens.append(f"4️⃣ Para chegar a 4% faltam {faltam[1]} chamadas.")
        mensagens.append(f"6️⃣ Para chegar a 6% faltam {faltam[2]} chamadas.")

    elif porcentagem >= 4:
        mensagens.append(f"1️⃣ Para chegar a 1% faltam {faltam[0]} chamadas.")
        mensagens.append(f"4️⃣ Para chegar a 4% faltam {faltam[1]} chamadas.")

    elif porcentagem >= 1:
        mensagens.append(f"1️⃣ Para chegar a 1% faltam {faltam[0]} chamadas.")

    else:
        mensagens.append("✅ Meta de abandono abaixo de 1% atingida.")
    print(f"DEBUG — mensagens: {mensagens}")
    return mensagens
#===================================================
ARQUIVO_RELATORIO = os.getenv("ARQUIVO_RELATORIO")
def apagar_relatorio_antigo():
    if os.path.exists(ARQUIVO_RELATORIO):
        os.remove(ARQUIVO_RELATORIO)
        print("Relatório antigo apagado.")
    else:
        print("Nenhum relatório antigo encontrado.")
def enviar_para_teams():
    driver = None
    try:
        options = Options()
        options.add_argument("--start-,minimized")
        options.add_argument("--disable-notifications")

        os.makedirs(CHROME_PROFILE, exist_ok=True)
        options.add_argument(f"--user-data-dir={CHROME_PROFILE}")
        options.add_argument("--profile-directory=Default")

        driver = webdriver.Chrome(options=options)

        wait = WebDriverWait(
            driver,
            120,
            ignored_exceptions=(StaleElementReferenceException,)
        )
        print("Abrindo o Teams")
        driver.get(URL_TEAMS)
        time.sleep(5)  # Aguarda 5 segundos para o Teams carregar
        txt_bar = (By.XPATH, '//div[@contenteditable="true"]')
        campo_mensagem = wait.until(lambda d: d.find_element(*txt_bar))
        mensagem = alerta_abandono()
        print("\nDEBUG — mensagem enviada:")
        print(repr(mensagem))
        campo_mensagem.click()
        time.sleep(2)
        for msg in mensagem:
            campo_mensagem.send_keys(msg)
        time.sleep(2)
        campo_mensagem.send_keys(Keys.ENTER)
        time.sleep(2)  # Aguarda 2 segundos para a mensagem ser enviada
    finally:
        if driver:
            driver.quit()
def baixar_relatorio():
    #abrir o navegador e baixar o relatório
    apagar_relatorio_antigo()
    driver = None
    try:
        options = Options()
        options.add_argument("--start-,minimized")
        options.add_argument("--disable-notifications")
        prefs = {
            "download.default_directory": PASTA_DOWNLOAD,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        options.add_experimental_option("prefs", prefs)
        os.makedirs(CHROME_PROFILE, exist_ok=True)
        options.add_argument(f"--user-data-dir={CHROME_PROFILE}")
        options.add_argument("--profile-directory=Default")
        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(
            driver,
            120,
            ignored_exceptions=(StaleElementReferenceException,)
        )
        #entrar no CRM
        driver.get("http://192.168.15.220/crm/index.php?codmodulo=112")
        wait.until(EC.presence_of_element_located((By.ID, "l_login"))).send_keys(USUARIO)
        driver.find_element(By.ID, "l_senha").send_keys(SENHA)
        driver.execute_script("enviarDados();")
        driver.get(URL_RELATORIO_1)
        busca_buton = wait.until(
            EC.element_to_be_clickable((By.ID, "btn_ids_campanha"))
        )
        busca_buton.click()
        filas = [
            "SAC Geral",
            "HotLine",
            "Perda e Roubo",
            "Receptivo Lojista"
        ]

        for fila in filas:
            checkbox = wait.until(
                EC.presence_of_element_located((
                    By.XPATH,
                    f"//tr[.//td[normalize-space()='{fila}']]//input[@type='checkbox']"
                ))
            )

            if not checkbox.is_selected():
                driver.execute_script("arguments[0].click();", checkbox)

        # botão Selecionar da janela
        wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[normalize-space()='Selecionar']")
            )
        ).click()
        time.sleep(2)  # Aguarda 2 segundos para a janela modal fechar
        # agora clique em Buscar
        botao_buscar = wait.until(
            EC.element_to_be_clickable((By.ID, "btn_pesquisar"))
        )
        botao_buscar.click()
        time.sleep(5)  # Aguarda 5 segundos para os resultados carregarem
        botao_excel = wait.until(
            EC.element_to_be_clickable((By.ID, "btn_excel"))
        )
        botao_excel.click()
        time.sleep(5)
    finally:
        if driver:
            driver.quit()
while True:
    baixar_relatorio()
    enviar_para_teams()
    time.sleep(1800)  # Aguarda meia hora antes de repetir o processo