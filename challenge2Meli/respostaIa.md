Resumo: A queda da Gi1/0/1 às 14:01:22 disparou uma reconvergência do Spanning Tree na VLAN10, com troca de root e mudança de estado 
nas portas Gi1/0/3 e Gi1/0/4. Logo depois apareceram dois problemas sem relação aparente com a queda: um duplex mismatch na Gi1/0/2 e 
uma violação de port security na Gi1/0/5. Por fim, alguém alterou a configuração via VTY a partir de 192.168.1.5.

Problemas encontrados
1. Queda da Gi1/0/1 com reconvergência do STP e troca de root na VLAN10

Gravidade: Alta

Evidência:
14:01:22.123 – %LINK-3-UPDOWN: GigabitEthernet1/0/1 changed state to down
14:01:22.125 – %LINEPROTO-5-UPDOWN: Line protocol on Gi1/0/1 changed state to down
14:01:23.101 – %SPANTREE-5-TOPO_CHANGE: Topology Change Notice received on VLAN0010
14:01:23.105 – Gi1/0/3 FORWARDING → BLOCKING
14:01:24.001 a 14:01:28.005 – Gi1/0/4 BLOCKING → LISTENING → LEARNING → FORWARDING
14:01:28.006 – %SPANTREE-5-ROOTCHANGE: New root is 00e0.b6ff.ee11, cost is 19, port Gi1/0/4

O que está acontecendo:
O link físico da Gi1/0/1 caiu. A queda do line protocol logo em seguida é só consequência disso.

Hipótese: a Gi1/0/1 era o caminho para o root bridge anterior. Sem ela, o STP recalculou a topologia, elegeu um novo root (00e0.b6ff.ee11)
acessível pela Gi1/0/4 e colocou a Gi1/0/3 em blocking.
A reconvergência levou cerca de 6 segundos. Durante esse tempo, a VLAN10 pode ter sofrido perda de tráfego.

Pontos suspeitos (hipóteses):
Os estados mudaram a cada 2 segundos. O padrão do 802.1D é 15 segundos de forward delay, então os timers podem ter sido alterados 
manualmente.
O custo 19 equivale a um enlace de 100 Mbps no método curto. Isso pode indicar que o caminho até o novo root está operando abaixo de 1 
Gbps.

Sugestão:
Verifique a camada física da Gi1/0/1 (cabo, SFP, porta do vizinho) com show interface Gi1/0/1 e show logging do equipamento do outro lado.
Confirme se o novo root é o esperado com show spanning-tree vlan 10. Se não for, fixe a prioridade do root desejado com spanning-tree vlan
10 root primary.
Revise os timers do STP. Se precisar de convergência rápida, prefira Rapid-PVST+ em vez de reduzir os timers do STP clássico.
Confira a velocidade negociada no caminho da Gi1/0/4.

2. Violação de port security na Gi1/0/5

Gravidade: Alta

Evidência: 14:01:32.500 – %PORT_SECURITY-2-PSECURE_VIOLATION: Security violation occurred on interface GigabitEthernet1/0/5

O que está acontecendo: Um MAC não autorizado tentou usar a porta, ou o limite de MACs da porta foi excedido. Hipótese: se o modo de 
violação for shutdown (o padrão), a porta está agora em err-disabled e o dispositivo legítimo ligado a ela está sem acesso. 
Pode ser apenas um equipamento trocado, mas também pode ser uma tentativa de acesso indevido.

Sugestão:
Rode show port-security interface Gi1/0/5 para ver o MAC que causou a violação e o modo configurado.
Identifique fisicamente o dispositivo conectado à porta.
Se for legítimo, ajuste os MACs permitidos e reative a porta com shutdown / no shutdown.
Se não for, mantenha a porta bloqueada e escale para segurança.

3. Duplex mismatch entre Gi1/0/2 e SW-Backup Gi0/1

Gravidade: Média

Evidência: 14:01:30.000 – %CDP-4-DUPLEX_MISMATCH: duplex mismatch discovered on GigabitEthernet1/0/2 (full), with SW-Backup 
GigabitEthernet0/1 (half)

O que está acontecendo: Um lado do enlace está em full duplex e o outro em half. Isso causa colisões tardias, erros de CRC e lentidão no 
link com o SW-Backup. O enlace não cai, por isso o problema costuma passar despercebido.

Sugestão:
Padronize os dois lados: ambos em auto (recomendado) ou ambos fixados em speed 1000 / duplex full.
Depois do ajuste, confira os contadores de erro e colisão com show interface Gi1/0/2.

4. Alteração de configuração logo após o incidente

Gravidade: Baixa

Evidência: 14:01:35.500 – %SYS-5-CONFIG_I: Configured from console by vty0 (192.168.1.5)

O que está acontecendo: A mensagem em si é informativa. O ponto de atenção é o horário: a configuração foi alterada 13 segundos depois 
da sequência de falhas. 

Hipótese: pode ser alguém tentando corrigir o problema ou uma mudança não relacionada (ou não autorizada). 
O log não mostra o que foi alterado.

Sugestão:
Identifique quem estava conectado a partir de 192.168.1.5 e confirme se a mudança foi autorizada.
Compare show running-config com a última configuração salva ou com o backup.
Se não houver, considere habilitar archive log config para registrar os comandos executados.

Eventos normais:
LINEPROTO down na Gi1/0/1: consequência esperada da queda do link físico (já incluída no problema 1).
Transições LISTENING → LEARNING → FORWARDING na Gi1/0/4: comportamento padrão de convergência do STP (o problema é o que as causou, 
não as transições em si).
Gi1/0/3 em BLOCKING: o STP evitando loop após recalcular a topologia, que é o funcionamento correto do protocolo.
SYS-5-CONFIG_I: registro informativo de alteração de configuração. Só merece atenção pelo horário (ver problema 4).
