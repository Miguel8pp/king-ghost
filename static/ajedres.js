// ajedres.js
const tablero = document.getElementById("tablero");
let turno = true; // true for Jugador 1 (blancas), false for Jugador 2 (negras)
const TurnoMostrar = document.getElementById("turnoActual");
const mensajeJuego = document.getElementById("mensajeJuego");
const piezasJ2 = document.getElementById("piezasJ2"); // Piezas blancas capturadas por J2
const piezasJ1 = document.getElementById("piezasJ1"); // Piezas negras capturadas por J1

// Modal elements
const startModal = document.getElementById("startModal");
const player1NameInput = document.getElementById("player1Name");
const player2NameInput = document.getElementById("player2Name");
const gameTimeInput = document.getElementById("gameTime"); // Nuevo input para el tiempo
const startButton = document.getElementById("startButton");
const skipButton = document.getElementById("skipButton");
const nameValidationMessage = document.getElementById("nameValidationMessage"); // Nuevo elemento para el mensaje de validación

const gameOverModal = document.getElementById("gameOverModal");
const gameOverMessage = document.getElementById("gameOverMessage");
const scoreDisplay = document.getElementById("scoreDisplay");
const rematchButton = document.getElementById("rematchButton");
const newGameButton = document.getElementById("newGameButton");

// Scorecard elements
const player1ScoreDisplay = document.getElementById("player1Score");
const player2ScoreDisplay = document.getElementById("player2Score");

let player1Name = "Jugador 1";
let player2Name = "Jugador 2";
let scorePlayer1 = 0;
let scorePlayer2 = 0;

// --- Variables del Temporizador ---
const timerContainer = document.getElementById("timerContainer"); // Contenedor del temporizador
const timerPlayer1Display = document.getElementById("timerPlayer1");
const timerPlayer2Display = document.getElementById("timerPlayer2");
let timeLimitSeconds = 300; // 5 minutos por defecto (5 * 60)
let gameHasTimeLimit = true; // Nuevo flag para controlar si se juega con tiempo
let currentPlayerTime = timeLimitSeconds; // Tiempo restante del jugador actual
let opponentPlayerTime = timeLimitSeconds; // Tiempo restante del oponente
let timerInterval; // Para almacenar el ID del intervalo del temporizador

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

let Posicion_actual_tablero = JSON.parse(
  JSON.stringify(Posicion_Inicial_Tablero)
); // Deep copy for resetting

let seleccion = null; // [fila, columna] de la pieza seleccionada
let boardClickEventHandler = null; // To store and remove event listener

// --- Funciones de Juego ---

function crearTablero() {
  tablero.innerHTML = ""; // Limpiar el tablero antes de crearlo
  for (let fila = 0; fila < 8; fila++) {
    for (let columna = 0; columna < 8; columna++) {
      const cuadro = document.createElement("div");
      cuadro.classList.add("cuadro");
      cuadro.classList.add((fila + columna) % 2 == 0 ? "blanco" : "negro");

      // Crear un span para la pieza para aplicar estilos de color y tamaño
      const piezaSpan = document.createElement("span");
      piezaSpan.textContent = Posicion_actual_tablero[fila][columna];
      if (Piezas_blancas(piezaSpan.textContent)) {
        piezaSpan.classList.add("pieza-blanca");
      } else if (Piezas_Negras(piezaSpan.textContent)) {
        piezaSpan.classList.add("pieza-negra");
      }
      cuadro.appendChild(piezaSpan); // Añadir el span al cuadro

      cuadro.dataset.fila = fila;
      cuadro.dataset.columna = columna;
      tablero.appendChild(cuadro);
    }
  }
  // Attach the event listener to the board once
  if (!boardClickEventHandler) {
    boardClickEventHandler = function (event) {
      let targetCuadro = event.target.closest(".cuadro");
      if (!targetCuadro) return; // Clicked outside a square

      const filaActual = parseInt(targetCuadro.dataset.fila);
      const columnaActual = parseInt(targetCuadro.dataset.columna);
      const piezaEnCuadro = Posicion_actual_tablero[filaActual][columnaActual];

      if (!seleccion) {
        // Si no hay pieza seleccionada, intentar seleccionar una
        if (
          (turno && Piezas_blancas(piezaEnCuadro)) ||
          (!turno && Piezas_Negras(piezaEnCuadro))
        ) {
          seleccion = [filaActual, columnaActual];
          targetCuadro.classList.add("seleccionado");
          Mostrar_Movimientos(filaActual, columnaActual, piezaEnCuadro);
        }
      } else {
        // Si ya hay una pieza seleccionada, intentar moverla o deseleccionar
        const filaOrigen = seleccion[0];
        const columnaOrigen = seleccion[1];
        const piezaSeleccionada =
          Posicion_actual_tablero[filaOrigen][columnaOrigen];

        if (filaActual === filaOrigen && columnaActual === columnaOrigen) {
          // Clic en la misma pieza seleccionada, deseleccionar
          limpiar_Movimientos();
          document
            .querySelector(
              `[data-fila="${filaOrigen}"][data-columna="${columnaOrigen}"]`
            )
            .classList.remove("seleccionado");
          seleccion = null;
        } else if (
          (turno && Piezas_blancas(piezaEnCuadro)) ||
          (!turno && Piezas_Negras(piezaEnCuadro))
        ) {
          // Clic en otra pieza del mismo color, cambiar selección
          limpiar_Movimientos();
          document
            .querySelector(
              `[data-fila="${filaOrigen}"][data-columna="${columnaOrigen}"]`
            )
            .classList.remove("seleccionado");
          seleccion = [filaActual, columnaActual];
          targetCuadro.classList.add("seleccionado");
          Mostrar_Movimientos(filaActual, columnaActual, piezaEnCuadro);
        } else {
          // Intentar mover a una nueva posición
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
            // Validar que el movimiento no ponga o deje al rey en jaque
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
              mensajeJuego.textContent =
                "¡Movimiento inválido! Tu rey estaría en jaque.";
              mensajeJuego.classList.add("mensaje-error");
              setTimeout(() => {
                mensajeJuego.textContent = "";
                mensajeJuego.classList.remove("mensaje-error");
              }, 2000);
              limpiar_Movimientos();
              document
                .querySelector(
                  `[data-fila="${filaOrigen}"][data-columna="${columnaOrigen}"]`
                )
                .classList.remove("seleccionado");
              seleccion = null;
            }
          } else {
            // Movimiento inválido, deseleccionar
            limpiar_Movimientos();
            document
              .querySelector(
                `[data-fila="${filaOrigen}"][data-columna="${columnaOrigen}"]`
              )
              .classList.remove("seleccionado");
            seleccion = null;
          }
        }
      }
    };
    tablero.addEventListener("click", boardClickEventHandler);
  }
}

function Piezas_blancas(pieza) {
  return ["♙", "♖", "♘", "♗", "♕", "♔"].includes(pieza);
}

function Piezas_Negras(pieza) {
  return ["♟", "♜", "♞", "♝", "♛", "♚"].includes(pieza);
}

function Peon_blanco(filaa, filaNueva, columnaa, columnaNueva, destino) {
  // Movimiento inicial de 2 casillas
  if (
    filaa === 6 &&
    filaNueva === 4 &&
    columnaa === columnaNueva &&
    Posicion_actual_tablero[5][columnaa] === "" &&
    destino === ""
  ) {
    return true;
  }
  // Movimiento de 1 casilla
  if (filaa - 1 === filaNueva && columnaa === columnaNueva && destino === "") {
    return true;
  }
  // Captura
  if (
    filaa - 1 === filaNueva &&
    (columnaa + 1 === columnaNueva || columnaa - 1 === columnaNueva) &&
    Piezas_Negras(destino)
  ) {
    return true;
  }
  return false;
}

function Peon_Negro(filaa, filaNueva, columnaa, columnaNueva, destino) {
  // Movimiento inicial de 2 casillas
  if (
    filaa === 1 &&
    filaNueva === 3 &&
    columnaa === columnaNueva &&
    Posicion_actual_tablero[2][columnaa] === "" &&
    destino === ""
  ) {
    return true;
  }
  // Movimiento de 1 casilla
  if (filaa + 1 === filaNueva && columnaa === columnaNueva && destino === "") {
    return true;
  }
  // Captura
  if (
    filaa + 1 === filaNueva &&
    (columnaa + 1 === columnaNueva || columnaa - 1 === columnaNueva) &&
    Piezas_blancas(destino)
  ) {
    return true;
  }
  return false;
}

function Torre(filaa, filaNueva, columnaa, columnaNueva, destino, tableroConsiderado) {
  if (filaa === filaNueva) {
    // Movimiento horizontal
    const paso = columnaNueva > columnaa ? 1 : -1;
    for (let i = columnaa + paso; i !== columnaNueva; i += paso) {
      if (tableroConsiderado[filaa][i] !== "") {
        return false; // Hay una pieza en el camino
      }
    }
    return true;
  } else if (columnaa === columnaNueva) {
    // Movimiento vertical
    const paso = filaNueva > filaa ? 1 : -1;
    for (let i = filaa + paso; i !== filaNueva; i += paso) {
      if (tableroConsiderado[i][columnaa] !== "") {
        return false; // Hay una pieza en el camino
      }
    }
    return true;
  }
  return false; // No es un movimiento de torre
}

function Caballo(filaa, filaNueva, columnaa, columnaNueva, destino) {
  const diffFila = Math.abs(filaNueva - filaa);
  const diffColumna = Math.abs(columnaNueva - columnaa);

  // Movimientos en L
  if (
    (diffFila === 2 && diffColumna === 1) ||
    (diffFila === 1 && diffColumna === 2)
  ) {
    return true;
  }
  return false;
}

function Alfil(filaa, filaNueva, columnaa, columnaNueva, destino, tableroConsiderado) {
  if (Math.abs(filaNueva - filaa) !== Math.abs(columnaNueva - columnaa)) {
    return false; // No es un movimiento diagonal
  }

  const paso_f = filaNueva > filaa ? 1 : -1;
  const paso_c = columnaNueva > columnaa ? 1 : -1;

  for (
    let i = filaa + paso_f, j = columnaa + paso_c;
    i !== filaNueva;
    i += paso_f, j += paso_c
  ) {
    if (tableroConsiderado[i][j] !== "") {
      return false; // Hay una pieza en el camino
    }
  }
  return true;
}

function Rey(filaa, filaNueva, columnaa, columnaNueva, destino) {
  const diffFila = Math.abs(filaNueva - filaa);
  const diffColumna = Math.abs(columnaNueva - columnaa);

  // Movimiento de una casilla en cualquier dirección
  return diffFila <= 1 && diffColumna <= 1;
}

function Reyna(filaa, filaNueva, columnaa, columnaNueva, destino, tableroConsiderado) {
  // La reina combina los movimientos de la torre y el alfil
  return (
    Torre(filaa, filaNueva, columnaa, columnaNueva, destino, tableroConsiderado) ||
    Alfil(filaa, filaNueva, columnaa, columnaNueva, destino, tableroConsiderado)
  );
}

function esMovimientoValido(
  pieza,
  filaa,
  columnaa,
  filaNueva,
  columnaNueva,
  destino,
  tableroConsiderado = Posicion_actual_tablero
) {
  // No se puede mover a una casilla con una pieza del mismo color
  const esPiezaBlanca = Piezas_blancas(pieza);
  const esPiezaNegra = Piezas_Negras(pieza);

  if (
    (esPiezaBlanca && Piezas_blancas(destino)) ||
    (esPiezaNegra && Piezas_Negras(destino))
  ) {
    return false;
  }

  switch (pieza) {
    case "♙":
      return Peon_blanco(filaa, filaNueva, columnaa, columnaNueva, destino);
    case "♟":
      return Peon_Negro(filaa, filaNueva, columnaa, columnaNueva, destino);
    case "♖":
    case "♜":
      return Torre(filaa, filaNueva, columnaa, columnaNueva, destino, tableroConsiderado);
    case "♘":
    case "♞":
      return Caballo(filaa, filaNueva, columnaa, columnaNueva, destino);
    case "♗":
    case "♝":
      return Alfil(filaa, filaNueva, columnaa, columnaNueva, destino, tableroConsiderado);
    case "♔":
    case "♚":
      return Rey(filaa, filaNueva, columnaa, columnaNueva, destino);
    case "♕":
    case "♛":
      return Reyna(filaa, filaNueva, columnaa, columnaNueva, destino, tableroConsiderado);
    default:
      return false;
  }
}

function Mostrar_Movimientos(fila, columna, pieza) {
  limpiar_Movimientos();
  mensajeJuego.textContent = ""; // Limpiar cualquier mensaje de error anterior

  for (let f = 0; f < 8; f++) {
    for (let c = 0; c < 8; c++) {
      const destino = Posicion_actual_tablero[f][c];
      if (
        esMovimientoValido(pieza, fila, columna, f, c, destino) &&
        !(fila === f && columna === c) // No marcar la casilla de origen como movimiento válido
      ) {
        // Simular el movimiento para verificar si el rey quedaría en jaque
        const tempTablero = JSON.parse(
          JSON.stringify(Posicion_actual_tablero)
        );
        const piezaOrigen = tempTablero[fila][columna];
        tempTablero[f][c] = piezaOrigen;
        tempTablero[fila][columna] = "";

        const cuadro = document.querySelector(
          `[data-fila="${f}"][data-columna="${c}"]`
        );

        if (!estaReyEnJaque(turno, tempTablero)) {
          cuadro.classList.add("movimiento-valido");
        } else {
          cuadro.classList.add("movimiento-invalido-check"); // Marcar en rojo
        }
      }
    }
  }
    // Detectar si el rey no tiene movimientos válidos
  if (pieza === (turno ? "♔" : "♚")) {
    const movimientosValidos = document.querySelectorAll(".movimiento-valido");
    const movimientosInvalidos = document.querySelectorAll(".movimiento-invalido-check");

    if (movimientosValidos.length === 0 && movimientosInvalidos.length > 0) {
      // Todos los movimientos están en rojo: jaque mate o rey sin escapatoria
      finalizarJuego(`${turno ? player2Name : player1Name} ha ganado por Jaque Mate.`);
    }
  }
}

function limpiar_Movimientos() {
  const cuadrosValidos = document.querySelectorAll(".movimiento-valido");
  cuadrosValidos.forEach((cuadro) =>
    cuadro.classList.remove("movimiento-valido")
  );
  const cuadrosInvalidos = document.querySelectorAll(
    ".movimiento-invalido-check"
  );
  cuadrosInvalidos.forEach((cuadro) =>
    cuadro.classList.remove("movimiento-invalido-check")
  );

  // Remove check highlight from king
  const reyCuadros = document.querySelectorAll(".en-jaque");
  reyCuadros.forEach((cuadro) => cuadro.classList.remove("en-jaque"));
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


function realizarMovimiento(
  filaa,
  columnaa,
  filaNueva,
  columnaNueva,
  pieza,
  destino
) {
  Posicion_actual_tablero[filaNueva][columnaNueva] = pieza;
  Posicion_actual_tablero[filaa][columnaa] = "";

  const Cuadro_Original = document.querySelector(
    `[data-fila="${filaa}"][data-columna="${columnaa}"]`
  );
  const Cuadro_Destino = document.querySelector(
    `[data-fila="${filaNueva}"][data-columna="${columnaNueva}"]`
  );

  // Si hay una pieza en el destino, añadirla a la lista de piezas eliminadas
  if (destino !== "") {
    Pieza_Eliminada(destino);
  }

  // Actualizar el contenido de los cuadros en el DOM
  Cuadro_Original.querySelector('span').textContent = "";
  Cuadro_Original.querySelector('span').classList.remove('pieza-blanca', 'pieza-negra');

  Cuadro_Destino.querySelector('span').textContent = pieza;
  Cuadro_Destino.querySelector('span').classList.remove('pieza-blanca', 'pieza-negra'); // Limpiar clases anteriores
  if (Piezas_blancas(pieza)) {
      Cuadro_Destino.querySelector('span').classList.add('pieza-blanca');
  } else if (Piezas_Negras(pieza)) {
      Cuadro_Destino.querySelector('span').classList.add('pieza-negra');
  }

  Cuadro_Original.classList.remove("seleccionado");
  limpiar_Movimientos();
  seleccion = null;
}

function cambiarTurno() {
  turno = !turno; // Invertir el turno para reflejar el siguiente jugador
  const reyEnJaque = estaReyEnJaque(turno, Posicion_actual_tablero);
  const [reyFila, reyColumna] = encontrarPosicionRey(turno, Posicion_actual_tablero);
  const reyCuadro = document.querySelector(`[data-fila="${reyFila}"][data-columna="${reyColumna}"]`);

  // Actualizar temporizadores y reiniciar el contador SOLO si hay límite de tiempo
  if (gameHasTimeLimit) {
    clearInterval(timerInterval); // Detener el temporizador del turno anterior
    // Asignar el tiempo restante del jugador actual al oponente antes de cambiar
    if (!turno) { // Si el próximo turno es de Negras (Jugador 2)
      opponentPlayerTime = currentPlayerTime; // El tiempo del J1 pasa a ser tiempo del oponente
      currentPlayerTime = timeLimitSeconds; // El tiempo del J2 se reinicia
      timerPlayer2Display.classList.add('active-timer');
      timerPlayer1Display.classList.remove('active-timer');
    } else { // Si el próximo turno es de Blancas (Jugador 1)
      opponentPlayerTime = currentPlayerTime; // El tiempo del J2 pasa a ser tiempo del oponente
      currentPlayerTime = timeLimitSeconds; // El tiempo del J1 se reinicia
      timerPlayer1Display.classList.add('active-timer');
      timerPlayer2Display.classList.remove('active-timer');
    }
    startTimer(); // Iniciar el temporizador para el nuevo turno
  }


  // Update turn display
  TurnoMostrar.textContent = `Turno: ${
    turno ? player1Name + " (Blancas)" : player2Name + " (Negras)"
  }`;

  // Clear previous messages and king highlight
  mensajeJuego.textContent = "";
  mensajeJuego.classList.remove("mensaje-jaque", "mensaje-jaque-mate", "mensaje-ahogado", "mensaje-error");
  document.querySelectorAll(".en-jaque").forEach(el => el.classList.remove("en-jaque"));


  if (reyEnJaque) {
    mensajeJuego.textContent = `¡El rey de ${turno ? player1Name : player2Name} está en jaque!`;
    mensajeJuego.classList.add("mensaje-jaque");
    reyCuadro.classList.add("en-jaque"); // Highlight king in check

    if (esJaqueMate(turno, Posicion_actual_tablero)) {
      finalizarJuego(`${turno ? player22Name : player1Name} ha ganado por Jaque Mate.`);
    }
  } else if (esAhogado(turno, Posicion_actual_tablero)) { // Nueva verificación para ahogado
      finalizarJuego(`¡Ahogado! El juego es un empate.`, true); // Pasar true para indicar empate
  }
}

// --- Nuevas funciones de Temporizador ---
function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
}

function updateTimerDisplay() {
  if (gameHasTimeLimit) {
    timerPlayer1Display.textContent = formatTime(turno ? currentPlayerTime : opponentPlayerTime);
    timerPlayer2Display.textContent = formatTime(turno ? opponentPlayerTime : currentPlayerTime);
    timerContainer.style.display = "flex"; // Mostrar el contenedor del temporizador
  } else {
    timerContainer.style.display = "none"; // Ocultar el contenedor si no hay límite de tiempo
  }
}

function startTimer() {
  if (!gameHasTimeLimit) {
    clearInterval(timerInterval);
    return; // No iniciar el temporizador si no hay límite de tiempo
  }

  clearInterval(timerInterval); // Asegurarse de que no haya múltiples intervalos
  timerInterval = setInterval(() => {
    if (turno) { // Jugador 1
      currentPlayerTime--;
      timerPlayer1Display.textContent = formatTime(currentPlayerTime);
      if (currentPlayerTime <= 0) {
        clearInterval(timerInterval);
        finalizarJuego(`${player2Name} ha ganado por tiempo.`);
      }
    } else { // Jugador 2
      currentPlayerTime--;
      timerPlayer2Display.textContent = formatTime(currentPlayerTime);
      if (currentPlayerTime <= 0) {
        clearInterval(timerInterval);
        finalizarJuego(`${player1Name} ha ganado por tiempo.`);
      }
    }
  }, 1000);
}

// --- Lógica de Jaque y Jaque Mate ---

function encontrarPosicionRey(esTurnoBlancas, tableroActual) {
  const reyBuscado = esTurnoBlancas ? "♔" : "♚";
  for (let r = 0; r < 8; r++) {
    for (let c = 0; c < 8; c++) {
      if (tableroActual[r][c] === reyBuscado) {
        return [r, c];
      }
    }
  }
  return null; // No debería ocurrir en un juego válido
}

function estaReyEnJaque(esTurnoBlancas, tableroActual) {
  const reyPos = encontrarPosicionRey(esTurnoBlancas, tableroActual);
  if (reyPos === null) return false; // Esto no debería suceder en un juego real
  const [reyFila, reyColumna] = reyPos;

  for (let r = 0; r < 8; r++) {
    for (let c = 0; c < 8; c++) {
      const piezaAtacante = tableroActual[r][c];
      const esPiezaAtacanteBlanca = Piezas_blancas(piezaAtacante);
      const esPiezaAtacanteNegra = Piezas_Negras(piezaAtacante);

      // Check if the piece is an opponent's piece
      if (
        piezaAtacante !== "" &&
        ((esTurnoBlancas && esPiezaAtacanteNegra) ||
          (!esTurnoBlancas && esPiezaAtacanteBlanca))
      ) {
        // Check if the attacking piece can move to the king's position
        // Pass a copy of the board for simulation
        if (
          esMovimientoValido(
            piezaAtacante,
            r,
            c,
            reyFila,
            reyColumna,
            tableroActual[reyFila][reyColumna], // The piece at king's position
            tableroActual
          )
        ) {
          return true; // King is in check
        }
      }
    }
  }
  return false; // King is not in check
}

function movimientoDejaReyEnJaque(
  filaOrigen,
  columnaOrigen,
  filaDestino,
  columnaDestino
) {
  // Simular el movimiento
  const tableroSimulado = JSON.parse(
    JSON.stringify(Posicion_actual_tablero)
  );
  const piezaMovida = tableroSimulado[filaOrigen][columnaOrigen];
  // const piezaEnDestino = tableroSimulado[filaDestino][columnaDestino]; // Store captured piece - no longer needed to restore since we use deep copy

  tableroSimulado[filaDestino][columnaDestino] = piezaMovida;
  tableroSimulado[filaOrigen][columnaOrigen] = "";

  // Verificar si el rey del jugador actual está en jaque en el tablero simulado
  const result = estaReyEnJaque(turno, tableroSimulado);

  // No es necesario restaurar tableroSimulado porque es una copia
  return result;
}

function tieneMovimientosLegales(esTurnoBlancas, tableroActual) {
    for (let r = 0; r < 8; r++) {
        for (let c = 0; c < 8; c++) {
            const pieza = tableroActual[r][c];
            if (pieza !== "" &&
                ((esTurnoBlancas && Piezas_blancas(pieza)) ||
                 (!esTurnoBlancas && Piezas_Negras(pieza)))) {

                // Para cada pieza, verifica si tiene al menos un movimiento legal
                for (let fDestino = 0; fDestino < 8; fDestino++) {
                    for (let cDestino = 0; cDestino < 8; cDestino++) {
                        const destinoTemp = tableroActual[fDestino][cDestino];

                        if (esMovimientoValido(pieza, r, c, fDestino, cDestino, destinoTemp, tableroActual)) {
                            // Simula el movimiento para ver si deja al rey en jaque
                            const tableroSimulado = JSON.parse(JSON.stringify(tableroActual));
                            tableroSimulado[fDestino][cDestino] = pieza;
                            tableroSimulado[r][c] = "";

                            if (!estaReyEnJaque(esTurnoBlancas, tableroSimulado)) {
                                return true; // Se encontró al menos un movimiento legal
                            }
                        }
                    }
                }
            }
        }
    }
    return false; // No se encontraron movimientos legales
}

function esJaqueMate(esTurnoBlancas, tableroActual) {
  return estaReyEnJaque(esTurnoBlancas, tableroActual) && !tieneMovimientosLegales(esTurnoBlancas, tableroActual);
}

// --- Nueva función para verificar Ahogado (Stalemate) ---
function esAhogado(esTurnoBlancas, tableroActual) {
    // Si el rey NO está en jaque y el jugador NO tiene movimientos legales, es ahogado.
    return !estaReyEnJaque(esTurnoBlancas, tableroActual) && !tieneMovimientosLegales(esTurnoBlancas, tableroActual);
}


function finalizarJuego(message, isDraw = false) {
    clearInterval(timerInterval); // Detener el temporizador final
    gameOverMessage.textContent = message;
    mensajeJuego.classList.remove("mensaje-jaque", "mensaje-jaque-mate", "mensaje-ahogado", "mensaje-error");
    mensajeJuego.textContent = ""; // Limpiar el mensaje de jaque/ahogado

    if (!isDraw) {
        // El turno ya ha cambiado al jugador que "perdió" (o cuyo rey está en jaque mate/tiempo).
        // Por lo tanto, el ganador es el *otro* jugador.
        if (turno) { // Si el turno actual es de las blancas (y perdieron), el ganador es el jugador 2
            scorePlayer2++;
        } else { // Si el turno actual es de las negras (y perdieron), el ganador es el jugador 1
            scorePlayer1++;
        }
    }
    // Actualizar el marcador de ganadas
    updateScorecard();

    scoreDisplay.textContent = `${player1Name} ${scorePlayer1} - ${scorePlayer2} ${player2Name}`;

    tablero.removeEventListener("click", boardClickEventHandler);
    gameOverModal.style.display = "flex";
    // Si hubo jaque mate, mantener el rey resaltado
    const [reyFila, reyColumna] = encontrarPosicionRey(turno, Posicion_actual_tablero);
    if (reyFila !== null && reyColumna !== null) {
        document.querySelector(`[data-fila="${reyFila}"][data-columna="${reyColumna}"]`).classList.add("en-jaque");
    }
}

// --- Actualizar el marcador de ganadas ---
function updateScorecard() {
  player1ScoreDisplay.textContent = scorePlayer1;
  player2ScoreDisplay.textContent = scorePlayer2;
}


// --- Funciones del Modal de Inicio ---
function showStartModal() {
  startModal.style.display = "flex";
  nameValidationMessage.textContent = ""; // Limpiar mensaje de validación al abrir el modal
}

startButton.addEventListener("click", () => {
  const p1 = player1NameInput.value.trim();
  const p2 = player2NameInput.value.trim();
  const time = parseInt(gameTimeInput.value);

  // Validación de nombres
  if (!p1 || !p2) {
    nameValidationMessage.textContent = "Por favor, ingresa un nombre para ambos jugadores o haz clic en Omitir.";
    return;
  }

  nameValidationMessage.textContent = ""; // Limpiar mensaje si la validación pasa

  player1Name = p1;
  player2Name = p2;

  if (time === 0) { // Si el tiempo es 0, no hay límite de tiempo
    gameHasTimeLimit = false;
  } else if (!isNaN(time) && time > 0) {
    timeLimitSeconds = time * 60; // Convertir minutos a segundos
    gameHasTimeLimit = true;
  } else { // Si no es un número válido o es negativo, por defecto con tiempo
    timeLimitSeconds = 300; // 5 minutos
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

// --- Funciones del Modal de Fin de Juego ---
rematchButton.addEventListener("click", () => {
  gameOverModal.style.display = "none";
  resetGame(false); // false for rematch, keeps scores
});

newGameButton.addEventListener("click", () => {
  gameOverModal.style.display = "none";
  resetGame(true); // true for new game, resets scores and names
  showStartModal(); // Show start modal again for new names
});

function resetBoard() {
  Posicion_actual_tablero = JSON.parse(
    JSON.stringify(Posicion_Inicial_Tablero)
  );
  piezasJ1.innerHTML = ""; // Usar innerHTML para limpiar todos los span
  piezasJ2.innerHTML = ""; // Usar innerHTML para limpiar todos los span
  seleccion = null;
  limpiar_Movimientos();
  crearTablero(); // Re-render the board with initial pieces
  // Re-attach event listener if it was removed
  if (!tablero.onclick) { // Check if the event handler is not already attached (or if it was removed)
      tablero.addEventListener("click", boardClickEventHandler);
  }
}

function resetGame(resetScoresAndNames = false) {
  resetBoard();
  // Reiniciar los tiempos
  if (gameHasTimeLimit) {
    currentPlayerTime = timeLimitSeconds;
    opponentPlayerTime = timeLimitSeconds;
  } else {
    currentPlayerTime = 0; // Asegurarse de que el tiempo esté en 0 si no hay límite
    opponentPlayerTime = 0;
  }
  updateTimerDisplay(); // Actualizar la vista del temporizador
  clearInterval(timerInterval); // Asegurarse de que no corra ningún temporizador

  if (resetScoresAndNames) {
    player1Name = "Jugador 1";
    player2Name = "Jugador 2";
    scorePlayer1 = 0;
    scorePlayer2 = 0;
    player1NameInput.value = "";
    player2NameInput.value = "";
    gameTimeInput.value = "5"; // Resetear el tiempo a 5 minutos
    gameHasTimeLimit = true; // Por defecto vuelve a tener tiempo
  }
  updateScorecard(); // Actualizar el marcador al reiniciar
  // Establecer el turno inicial correctamente
  turno = true; // Siempre empieza Jugador 1 (Blancas)
  cambiarTurnoDisplayAndTimer(); // Llamar a una nueva función para actualizar el display y el timer
}

// Nueva función para manejar la actualización del display de turno y el temporizador
function cambiarTurnoDisplayAndTimer() {
  // Update turn display
  TurnoMostrar.textContent = `Turno: ${
    turno ? player1Name + " (Blancas)" : player2Name + " (Negras)"
  }`;

  // Actualizar temporizadores y reiniciar el contador SOLO si hay límite de tiempo
  if (gameHasTimeLimit) {
    clearInterval(timerInterval); // Detener cualquier temporizador existente
    // Asignar el tiempo restante del jugador actual y oponente
    if (turno) { // Turno del Jugador 1 (Blancas)
        timerPlayer1Display.classList.add('active-timer');
        timerPlayer2Display.classList.remove('active-timer');
    } else { // Turno del Jugador 2 (Negras)
        timerPlayer2Display.classList.add('active-timer');
        timerPlayer1Display.classList.remove('active-timer');
    }
    startTimer(); // Iniciar el temporizador para el jugador actual
  } else {
    // Si no hay límite de tiempo, asegurarse de que no haya timers activos y los displays estén apagados
    clearInterval(timerInterval);
    timerPlayer1Display.classList.remove('active-timer');
    timerPlayer2Display.classList.remove('active-timer');
  }

  // Clear previous messages and king highlight
  mensajeJuego.textContent = "";
  mensajeJuego.classList.remove("mensaje-jaque", "mensaje-jaque-mate", "mensaje-ahogado", "mensaje-error");
  document.querySelectorAll(".en-jaque").forEach(el => el.classList.remove("en-jaque"));

  const reyEnJaque = estaReyEnJaque(turno, Posicion_actual_tablero);
  const [reyFila, reyColumna] = encontrarPosicionRey(turno, Posicion_actual_tablero);
  const reyCuadro = document.querySelector(`[data-fila="${reyFila}"][data-columna="${reyColumna}"]`);

  if (reyEnJaque) {
    mensajeJuego.textContent = `¡El rey de ${turno ? player1Name : player2Name} está en jaque!`;
    mensajeJuego.classList.add("mensaje-jaque");
    reyCuadro.classList.add("en-jaque"); // Highlight king in check

    if (esJaqueMate(turno, Posicion_actual_tablero)) {
      finalizarJuego(`${turno ? player2Name : player1Name} ha ganado por Jaque Mate.`);
    }
  } else if (esAhogado(turno, Posicion_actual_tablero)) {
      finalizarJuego(`¡Ahogado! El juego es un empate.`, true);
  }
}


function startGame() {
  resetBoard();
  // Inicializar y mostrar los temporizadores al inicio del juego
  if (gameHasTimeLimit) {
    currentPlayerTime = timeLimitSeconds;
    opponentPlayerTime = timeLimitSeconds;
    timerContainer.style.display = "flex";
  } else {
    timerContainer.style.display = "none";
  }
  updateTimerDisplay();
  updateScorecard(); // Actualizar el marcador al iniciar

  // Establecer el turno inicial correctamente
  turno = false; // Se establece en false para que la primera llamada a cambiarTurno lo cambie a true
  cambiarTurno(); // Esto lo cambiará a "true" y configurará el display para Jugador 1 (Blancas)
}

// Show the start modal when the page loads
window.onload = showStartModal;