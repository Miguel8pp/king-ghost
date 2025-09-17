const tablero = document.getElementById("tablero");
let turno = true; 
const TurnoMostrar = document.getElementById("turnoActual");
const mensajeJuego = document.getElementById("mensajeJuego");
const piezasJ2 = document.getElementById("piezasJ2"); 
const piezasJ1 = document.getElementById("piezasJ1"); 

const startModal = document.getElementById("startModal");
const player1NameInput = document.getElementById("player1Name");
const player2NameInput = document.getElementById("player2Name");
const gameTimeInput = document.getElementById("gameTime");
const startButton = document.getElementById("startButton");
const skipButton = document.getElementById("skipButton");
const nameValidationMessage = document.getElementById("nameValidationMessage");

const gameOverModal = document.getElementById("gameOverModal");
const gameOverMessage = document.getElementById("gameOverMessage");
const scoreDisplay = document.getElementById("scoreDisplay");
const rematchButton = document.getElementById("rematchButton");
const newGameButton = document.getElementById("newGameButton");

const player1ScoreDisplay = document.getElementById("player1Score");
const player2ScoreDisplay = document.getElementById("player2Score");

let player1Name = "Jugador 1";
let player2Name = "Jugador 2";
let scorePlayer1 = 0;
let scorePlayer2 = 0;

const timerContainer = document.getElementById("timerContainer");
const timerPlayer1Display = document.getElementById("timerPlayer1");
const timerPlayer2Display = document.getElementById("timerPlayer2");
let timeLimitSeconds = 300; 
let gameHasTimeLimit = true;
let player1TimeRemaining = timeLimitSeconds;
let player2TimeRemaining = timeLimitSeconds;
let timerInterval;

const Posicion_Inicial_Tablero = [
  ["♜", "♞", "♝", "♛", "♚", "♝", "♞", "♜"],
  ["♟", "♟", "♟", "♟", "♟", "♟", "♟", "♟"],
  ["", "", "", "", "", "", "", ""],
  ["", "", "", "", "", "", "", ""],
  ["", "", "", "", "", "", "", ""],
  ["", "", "", "", "", "", "", ""],
  ["♙", "♙", "♙", "♙", "♙", "♙", "♙", "♙"],
  ["♖", "♘", "♗", "♕", "♔", "♗", "♘", "♖"],
];

let Posicion_actual_tablero = JSON.parse(JSON.stringify(Posicion_Inicial_Tablero));
let seleccion = null;


function crearTablero() {
  tablero.innerHTML = "";
  for (let fila = 0; fila < 8; fila++) {
    for (let columna = 0; columna < 8; columna++) {
      const cuadro = document.createElement("div");
      cuadro.classList.add("cuadro");
      cuadro.classList.add((fila + columna) % 2 == 0 ? "blanco" : "negro");

      const piezaSpan = document.createElement("span");
      piezaSpan.textContent = Posicion_actual_tablero[fila][columna];
      if (Piezas_blancas(piezaSpan.textContent)) {
        piezaSpan.classList.add("pieza-blanca");
      } else if (Piezas_Negras(piezaSpan.textContent)) {
        piezaSpan.classList.add("pieza-negra");
      }
      cuadro.appendChild(piezaSpan);

      cuadro.dataset.fila = fila;
      cuadro.dataset.columna = columna;
      tablero.appendChild(cuadro);
    }
  }
  
  tablero.removeEventListener("click", handleBoardClick);
  tablero.addEventListener("click", handleBoardClick);
}

function handleBoardClick(event) {
  let targetCuadro = event.target.closest(".cuadro");
  if (!targetCuadro) return;

  const filaActual = parseInt(targetCuadro.dataset.fila);
  const columnaActual = parseInt(targetCuadro.dataset.columna);
  const piezaEnCuadro = Posicion_actual_tablero[filaActual][columnaActual];

  if (!seleccion) {
    if (
      (turno && Piezas_blancas(piezaEnCuadro)) ||
      (!turno && Piezas_Negras(piezaEnCuadro))
    ) {
      seleccion = [filaActual, columnaActual];
      targetCuadro.classList.add("seleccionado");
      Mostrar_Movimientos(filaActual, columnaActual, piezaEnCuadro);
    }
  } else {
    const filaOrigen = seleccion[0];
    const columnaOrigen = seleccion[1];
    const piezaSeleccionada = Posicion_actual_tablero[filaOrigen][columnaOrigen];

    if (filaActual === filaOrigen && columnaActual === columnaOrigen) {
      limpiar_Movimientos();
      document.querySelector(`[data-fila="${filaOrigen}"][data-columna="${columnaOrigen}"]`)
        .classList.remove("seleccionado");
      seleccion = null;
    } else if (
      (turno && Piezas_blancas(piezaEnCuadro)) ||
      (!turno && Piezas_Negras(piezaEnCuadro))
    ) {
      limpiar_Movimientos();
      document.querySelector(`[data-fila="${filaOrigen}"][data-columna="${columnaOrigen}"]`)
        .classList.remove("seleccionado");
      seleccion = [filaActual, columnaActual];
      targetCuadro.classList.add("seleccionado");
      Mostrar_Movimientos(filaActual, columnaActual, piezaEnCuadro);
    } else {
      if (
        esMovimientoValido(
          piezaSeleccionada,
          filaOrigen,
          columnaOrigen,
          filaActual,
          columnaActual,
          piezaEnCuadro
        )
      ) {
        if (
          !movimientoDejaReyEnJaque(
            filaOrigen,
            columnaOrigen,
            filaActual,
            columnaActual
          )
        ) {
          realizarMovimiento(
            filaOrigen,
            columnaOrigen,
            filaActual,
            columnaActual,
            piezaSeleccionada,
            piezaEnCuadro
          );
          cambiarTurno();
        } else {
          mostrarError("¡Movimiento inválido! Tu rey estaría en jaque.");
        }
      } else {
        limpiar_Movimientos();
        document.querySelector(`[data-fila="${filaOrigen}"][data-columna="${columnaOrigen}"]`)
          .classList.remove("seleccionado");
        seleccion = null;
      }
    }
  }
}

function mostrarError(mensaje) {
  mensajeJuego.textContent = mensaje;
  mensajeJuego.classList.add("mensaje-error");
  setTimeout(() => {
    mensajeJuego.textContent = "";
    mensajeJuego.classList.remove("mensaje-error");
  }, 2000);
  
  limpiar_Movimientos();
  if (seleccion) {
    document.querySelector(`[data-fila="${seleccion[0]}"][data-columna="${seleccion[1]}"]`)
      .classList.remove("seleccionado");
    seleccion = null;
  }
}

function Piezas_blancas(pieza) {
  return ["♙", "♖", "♘", "♗", "♕", "♔"].includes(pieza);
}

function Piezas_Negras(pieza) {
  return ["♟", "♜", "♞", "♝", "♛", "♚"].includes(pieza);
}

function movimientoDejaReyEnJaque(filaOrigen, columnaOrigen, filaDestino, columnaDestino) {
  const tableroSimulado = JSON.parse(JSON.stringify(Posicion_actual_tablero));
  const piezaMovida = tableroSimulado[filaOrigen][columnaOrigen];
  const piezaFinal = verificarPromocionPeon(piezaMovida, filaDestino);
  
  tableroSimulado[filaDestino][columnaDestino] = piezaFinal;
  tableroSimulado[filaOrigen][columnaOrigen] = "";

  return estaReyEnJaque(turno, tableroSimulado);
}

function tieneMovimientosLegales(esTurnoBlancas, tableroActual) {
  for (let r = 0; r < 8; r++) {
    for (let c = 0; c < 8; c++) {
      const pieza = tableroActual[r][c];
      if (pieza !== "" &&
          ((esTurnoBlancas && Piezas_blancas(pieza)) ||
           (!esTurnoBlancas && Piezas_Negras(pieza)))) {

        for (let fDestino = 0; fDestino < 8; fDestino++) {
          for (let cDestino = 0; cDestino < 8; cDestino++) {
            const destinoTemp = tableroActual[fDestino][cDestino];

            if (esMovimientoValido(pieza, r, c, fDestino, cDestino, destinoTemp, tableroActual)) {
              const tableroSimulado = JSON.parse(JSON.stringify(tableroActual));
              const piezaFinal = verificarPromocionPeon(pieza, fDestino);
              
              tableroSimulado[fDestino][cDestino] = piezaFinal;
              tableroSimulado[r][c] = "";

              if (!estaReyEnJaque(esTurnoBlancas, tableroSimulado)) {
                return true;
              }
            }
          }
        }
      }
    }
  }
  return false;
}

function esJaqueMate(esTurnoBlancas, tableroActual) {
  return estaReyEnJaque(esTurnoBlancas, tableroActual) && !tieneMovimientosLegales(esTurnoBlancas, tableroActual);
}

function esAhogado(esTurnoBlancas, tableroActual) {
  return !estaReyEnJaque(esTurnoBlancas, tableroActual) && !tieneMovimientosLegales(esTurnoBlancas, tableroActual);
}

function finalizarJuego(message, isDraw = false) {
  clearInterval(timerInterval);
  gameOverMessage.textContent = message;
  mensajeJuego.classList.remove("mensaje-jaque", "mensaje-jaque-mate", "mensaje-ahogado", "mensaje-error", "mensaje-promocion");
  mensajeJuego.textContent = "";

  if (!isDraw) {
    if (turno) {
      scorePlayer2++;
    } else {
      scorePlayer1++;
    }
  }
  
  updateScorecard();
  scoreDisplay.textContent = `${player1Name} ${scorePlayer1} - ${scorePlayer2} ${player2Name}`;

  tablero.removeEventListener("click", handleBoardClick);
  gameOverModal.style.display = "flex";
  
  if (!isDraw) {
    const [reyFila, reyColumna] = encontrarPosicionRey(turno, Posicion_actual_tablero);
    if (reyFila !== null && reyColumna !== null) {
      document.querySelector(`[data-fila="${reyFila}"][data-columna="${reyColumna}"]`).classList.add("en-jaque");
    }
  }
}

function updateScorecard() {
  player1ScoreDisplay.textContent = scorePlayer1;
  player2ScoreDisplay.textContent = scorePlayer2;
}

function formatTime(seconds) {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
}

function updateTimerDisplay() {
  if (gameHasTimeLimit) {
    timerPlayer1Display.textContent = formatTime(player1TimeRemaining);
    timerPlayer2Display.textContent = formatTime(player2TimeRemaining);
    timerContainer.style.display = "flex";
    
    if (turno) {
      timerPlayer1Display.classList.add('active-timer');
      timerPlayer2Display.classList.remove('active-timer');
    } else {
      timerPlayer2Display.classList.add('active-timer');
      timerPlayer1Display.classList.remove('active-timer');
    }
  } else {
    timerContainer.style.display = "none";
  }
}

function startTimer() {
  if (!gameHasTimeLimit) {
    clearInterval(timerInterval);
    return;
  }

  clearInterval(timerInterval);
  timerInterval = setInterval(() => {
    if (turno) {
      player1TimeRemaining--;
      if (player1TimeRemaining <= 0) {
        clearInterval(timerInterval);
        finalizarJuego(`${player2Name} ha ganado por tiempo.`);
        return;
      }
    } else {
      player2TimeRemaining--;
      if (player2TimeRemaining <= 0) {
        clearInterval(timerInterval);
        finalizarJuego(`${player1Name} ha ganado por tiempo.`);
        return;
      }
    }
    updateTimerDisplay();
  }, 1000);
}

function showStartModal() {
  startModal.style.display = "flex";
  nameValidationMessage.textContent = "";
}

startButton.addEventListener("click", () => {
  const p1 = player1NameInput.value.trim();
  const p2 = player2NameInput.value.trim();
  const time = parseInt(gameTimeInput.value);

  if (!p1 || !p2) {
    nameValidationMessage.textContent = "Por favor, ingresa un nombre para ambos jugadores o haz clic en Omitir.";
    return;
  }

  nameValidationMessage.textContent = "";
  player1Name = p1;
  player2Name = p2;

  if (time === 0) {
    gameHasTimeLimit = false;
  } else if (!isNaN(time) && time > 0) {
    timeLimitSeconds = time * 60;
    gameHasTimeLimit = true;
  } else {
    timeLimitSeconds = 300;
    gameHasTimeLimit = true;
  }

  startModal.style.display = "none";
  startGame();
});

skipButton.addEventListener("click", () => {
  player1Name = "Jugador 1";
  player2Name = "Jugador 2";
  const time = parseInt(gameTimeInput.value);

  if (time === 0) {
    gameHasTimeLimit = false;
  } else if (!isNaN(time) && time > 0) {
    timeLimitSeconds = time * 60;
    gameHasTimeLimit = true;
  } else {
    timeLimitSeconds = 300;
    gameHasTimeLimit = true;
  }

  startModal.style.display = "none";
  startGame();
});

rematchButton.addEventListener("click", () => {
  gameOverModal.style.display = "none";
  resetGame(false);
});

newGameButton.addEventListener("click", () => {
  gameOverModal.style.display = "none";
  resetGame(true);
  showStartModal();
});

function resetBoard() {
  Posicion_actual_tablero = JSON.parse(JSON.stringify(Posicion_Inicial_Tablero));
  piezasJ1.innerHTML = "";
  piezasJ2.innerHTML = "";
  seleccion = null;
  limpiar_Movimientos();
  crearTablero();
}

function resetGame(resetScoresAndNames = false) {
  resetBoard();
  
  player1TimeRemaining = timeLimitSeconds;
  player2TimeRemaining = timeLimitSeconds;
  clearInterval(timerInterval);

  if (resetScoresAndNames) {
    player1Name = "Jugador 1";
    player2Name = "Jugador 2";
    scorePlayer1 = 0;
    scorePlayer2 = 0;
    player1NameInput.value = "";
    player2NameInput.value = "";
    gameTimeInput.value = "5";
    gameHasTimeLimit = true;
  }
  
  updateScorecard();
  turno = true;
  cambiarTurnoDisplay();
}

function startGame() {
  resetBoard();
  
  if (gameHasTimeLimit) {
    player1TimeRemaining = timeLimitSeconds;
    player2TimeRemaining = timeLimitSeconds;
  }
  
  updateScorecard();
  turno = true;
  cambiarTurnoDisplay();
  
  if (gameHasTimeLimit) {
    startTimer();
  }
}

function cambiarTurnoDisplay() {
  TurnoMostrar.textContent = `Turno: ${turno ? player1Name + " (Blancas)" : player2Name + " (Negras)"}`;
  
  updateTimerDisplay();
  
  mensajeJuego.textContent = "";
  mensajeJuego.classList.remove("mensaje-jaque", "mensaje-jaque-mate", "mensaje-ahogado", "mensaje-error", "mensaje-promocion");
  document.querySelectorAll(".en-jaque").forEach(el => el.classList.remove("en-jaque"));

  const reyEnJaque = estaReyEnJaque(turno, Posicion_actual_tablero);
  const [reyFila, reyColumna] = encontrarPosicionRey(turno, Posicion_actual_tablero);
  
  if (reyFila !== null && reyColumna !== null) {
    const reyCuadro = document.querySelector(`[data-fila="${reyFila}"][data-columna="${reyColumna}"]`);
    
    if (reyEnJaque) {
      mensajeJuego.textContent = `¡El rey de ${turno ? player1Name : player2Name} está en jaque!`;
      mensajeJuego.classList.add("mensaje-jaque");
      reyCuadro.classList.add("en-jaque");

      if (esJaqueMate(turno, Posicion_actual_tablero)) {
        finalizarJuego(`${turno ? player2Name : player1Name} ha ganado por Jaque Mate.`);
      }
    } else if (esAhogado(turno, Posicion_actual_tablero)) {
      finalizarJuego(`¡Ahogado! El juego es un empate.`, true);
    }
  }
}

function Peon_blanco(filaa, filaNueva, columnaa, columnaNueva, destino) {
  if (filaa === 6 && filaNueva === 4 && columnaa === columnaNueva && 
      Posicion_actual_tablero[5][columnaa] === "" && destino === "") {
    return true;
  }
  if (filaa - 1 === filaNueva && columnaa === columnaNueva && destino === "") {
    return true;
  }
  if (filaa - 1 === filaNueva && 
      (columnaa + 1 === columnaNueva || columnaa - 1 === columnaNueva) && 
      Piezas_Negras(destino)) {
    return true;
  }
  return false;
}

function Peon_Negro(filaa, filaNueva, columnaa, columnaNueva, destino) {
  if (filaa === 1 && filaNueva === 3 && columnaa === columnaNueva && 
      Posicion_actual_tablero[2][columnaa] === "" && destino === "") {
    return true;
  }
  if (filaa + 1 === filaNueva && columnaa === columnaNueva && destino === "") {
    return true;
  }
  if (filaa + 1 === filaNueva && 
      (columnaa + 1 === columnaNueva || columnaa - 1 === columnaNueva) && 
      Piezas_blancas(destino)) {
    return true;
  }
  return false;
}

function Torre(filaa, filaNueva, columnaa, columnaNueva, destino, tableroConsiderado) {
  if (filaa === filaNueva) {
    const paso = columnaNueva > columnaa ? 1 : -1;
    for (let i = columnaa + paso; i !== columnaNueva; i += paso) {
      if (tableroConsiderado[filaa][i] !== "") {
        return false;
      }
    }
    return true;
  } else if (columnaa === columnaNueva) {
    const paso = filaNueva > filaa ? 1 : -1;
    for (let i = filaa + paso; i !== filaNueva; i += paso) {
      if (tableroConsiderado[i][columnaa] !== "") {
        return false;
      }
    }
    return true;
  }
  return false;
}

function Caballo(filaa, filaNueva, columnaa, columnaNueva, destino) {
  const diffFila = Math.abs(filaNueva - filaa);
  const diffColumna = Math.abs(columnaNueva - columnaa);
  return (diffFila === 2 && diffColumna === 1) || (diffFila === 1 && diffColumna === 2);
}

function Alfil(filaa, filaNueva, columnaa, columnaNueva, destino, tableroConsiderado) {
  if (Math.abs(filaNueva - filaa) !== Math.abs(columnaNueva - columnaa)) {
    return false;
  }

  const paso_f = filaNueva > filaa ? 1 : -1;
  const paso_c = columnaNueva > columnaa ? 1 : -1;

  for (let i = filaa + paso_f, j = columnaa + paso_c; i !== filaNueva; i += paso_f, j += paso_c) {
    if (tableroConsiderado[i][j] !== "") {
      return false;
    }
  }
  return true;
}

function Rey(filaa, filaNueva, columnaa, columnaNueva, destino) {
  const diffFila = Math.abs(filaNueva - filaa);
  const diffColumna = Math.abs(columnaNueva - columnaa);
  return diffFila <= 1 && diffColumna <= 1;
}

function Reyna(filaa, filaNueva, columnaa, columnaNueva, destino, tableroConsiderado) {
  return Torre(filaa, filaNueva, columnaa, columnaNueva, destino, tableroConsiderado) ||
         Alfil(filaa, filaNueva, columnaa, columnaNueva, destino, tableroConsiderado);
}

function esMovimientoValido(pieza, filaa, columnaa, filaNueva, columnaNueva, destino, tableroConsiderado = Posicion_actual_tablero) {
  const esPiezaBlanca = Piezas_blancas(pieza);
  const esPiezaNegra = Piezas_Negras(pieza);

  if ((esPiezaBlanca && Piezas_blancas(destino)) || (esPiezaNegra && Piezas_Negras(destino))) {
    return false;
  }

  switch (pieza) {
    case "♙": return Peon_blanco(filaa, filaNueva, columnaa, columnaNueva, destino);
    case "♟": return Peon_Negro(filaa, filaNueva, columnaa, columnaNueva, destino);
    case "♖": case "♜": return Torre(filaa, filaNueva, columnaa, columnaNueva, destino, tableroConsiderado);
    case "♘": case "♞": return Caballo(filaa, filaNueva, columnaa, columnaNueva, destino);
    case "♗": case "♝": return Alfil(filaa, filaNueva, columnaa, columnaNueva, destino, tableroConsiderado);
    case "♔": case "♚": return Rey(filaa, filaNueva, columnaa, columnaNueva, destino);
    case "♕": case "♛": return Reyna(filaa, filaNueva, columnaa, columnaNueva, destino, tableroConsiderado);
    default: return false;
  }
}

function verificarPromocionPeon(pieza, filaDestino) {
  if (pieza === "♙" && filaDestino === 0) return "♕";
  if (pieza === "♟" && filaDestino === 7) return "♛";
  return pieza;
}

function Mostrar_Movimientos(fila, columna, pieza) {
  limpiar_Movimientos();
  mensajeJuego.textContent = "";

  for (let f = 0; f < 8; f++) {
    for (let c = 0; c < 8; c++) {
      const destino = Posicion_actual_tablero[f][c];
      if (esMovimientoValido(pieza, fila, columna, f, c, destino) && !(fila === f && columna === c)) {
        const tempTablero = JSON.parse(JSON.stringify(Posicion_actual_tablero));
        const piezaFinal = verificarPromocionPeon(pieza, f);
        tempTablero[f][c] = piezaFinal;
        tempTablero[fila][columna] = "";

        const cuadro = document.querySelector(`[data-fila="${f}"][data-columna="${c}"]`);

        if (!estaReyEnJaque(turno, tempTablero)) {
          cuadro.classList.add("movimiento-valido");
        } else {
          cuadro.classList.add("movimiento-invalido-check");
        }
      }
    }
  }
}

function limpiar_Movimientos() {
  document.querySelectorAll(".movimiento-valido").forEach(cuadro => cuadro.classList.remove("movimiento-valido"));
  document.querySelectorAll(".movimiento-invalido-check").forEach(cuadro => cuadro.classList.remove("movimiento-invalido-check"));
  document.querySelectorAll(".en-jaque").forEach(cuadro => cuadro.classList.remove("en-jaque"));
}

function Pieza_Eliminada(piezaEliminada) {
  const spanPieza = document.createElement("span");
  spanPieza.textContent = piezaEliminada;
  if (Piezas_Negras(piezaEliminada)) {
    spanPieza.classList.add("pieza-negra");
    piezasJ2.appendChild(spanPieza);
  } else if (Piezas_blancas(piezaEliminada)) {
    spanPieza.classList.add("pieza-blanca");
    piezasJ1.appendChild(spanPieza);
  }
}

function realizarMovimiento(filaa, columnaa, filaNueva, columnaNueva, pieza, destino) {
  const piezaFinal = verificarPromocionPeon(pieza, filaNueva);
  
  Posicion_actual_tablero[filaNueva][columnaNueva] = piezaFinal;
  Posicion_actual_tablero[filaa][columnaa] = "";

  const cuadroOriginal = document.querySelector(`[data-fila="${filaa}"][data-columna="${columnaa}"]`);
  const cuadroDestino = document.querySelector(`[data-fila="${filaNueva}"][data-columna="${columnaNueva}"]`);

  if (destino !== "") {
    Pieza_Eliminada(destino);
  }

  cuadroOriginal.querySelector('span').textContent = "";
  cuadroOriginal.querySelector('span').classList.remove('pieza-blanca', 'pieza-negra');

  cuadroDestino.querySelector('span').textContent = piezaFinal;
  cuadroDestino.querySelector('span').classList.remove('pieza-blanca', 'pieza-negra');
  if (Piezas_blancas(piezaFinal)) {
    cuadroDestino.querySelector('span').classList.add('pieza-blanca');
  } else if (Piezas_Negras(piezaFinal)) {
    cuadroDestino.querySelector('span').classList.add('pieza-negra');
  }

  cuadroOriginal.classList.remove("seleccionado");
  limpiar_Movimientos();
  seleccion = null;
  
  if (piezaFinal !== pieza) {
    const jugadorActual = turno ? player1Name : player2Name;
    mensajeJuego.textContent = `¡${jugadorActual} ha promocionado un peón a reina!`;
    mensajeJuego.classList.add("mensaje-promocion");
    setTimeout(() => {
      mensajeJuego.textContent = "";
      mensajeJuego.classList.remove("mensaje-promocion");
    }, 3000);
  }
}

function cambiarTurno() {
  turno = !turno;
  
  if (gameHasTimeLimit) {
    clearInterval(timerInterval);
    startTimer();
  }
  
  cambiarTurnoDisplay();
}

function encontrarPosicionRey(esTurnoBlancas, tableroActual) {
  const reyBuscado = esTurnoBlancas ? "♔" : "♚";
  for (let r = 0; r < 8; r++) {
    for (let c = 0; c < 8; c++) {
      if (tableroActual[r][c] === reyBuscado) {
        return [r, c];
      }
    }
  }
  return [null, null];
}

function estaReyEnJaque(esTurnoBlancas, tableroActual) {
  const [reyFila, reyColumna] = encontrarPosicionRey(esTurnoBlancas, tableroActual);
  if (reyFila === null) return false;

  for (let r = 0; r < 8; r++) {
    for (let c = 0; c < 8; c++) {
      const piezaAtacante = tableroActual[r][c];
      const esPiezaAtacanteBlanca = Piezas_blancas(piezaAtacante);
      const esPiezaAtacanteNegra = Piezas_Negras(piezaAtacante);

      if (piezaAtacante !== "" &&
          ((esTurnoBlancas && esPiezaAtacanteNegra) ||
           (!esTurnoBlancas && esPiezaAtacanteBlanca))) {
        
        if (esMovimientoValido(piezaAtacante, r, c, reyFila, reyColumna, tableroActual[reyFila][reyColumna], tableroActual)) {
          return true;
        }
      }
    }
  }
  return false;
}

window.onload = showStartModal;