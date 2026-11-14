/*
   static/js/arkhe.js
   Comportamiento comun de todas las pantallas (lo carga base.html).

   Regla de este archivo: las plantillas NO llevan JavaScript en linea
   (nada de onclick="..." ni onsubmit="..."). Cada elemento declara lo
   que quiere con un atributo data-..., y aqui se le da el comportamiento.
   Asi los datos escritos por los usuarios (nombres de proyectos, de
   clientes, etc.) nunca se mezclan con codigo JavaScript.

     data-abrir-modal="id"     boton que abre la ventana modal #id
     data-cerrar-modal         boton que cierra la modal que lo contiene
     data-cerrar-alerta        boton que quita un mensaje flash
     data-confirmar="texto"    formulario que pide confirmacion antes de enviarse
     data-confirmar-boton      (opcional) texto del boton de aceptar
*/

(function () {
  "use strict";

  /* ---------- Ventanas modales ---------- */

  var ultimoFoco = null; // para devolver el foco al cerrar

  function abrirModal(modal) {
    if (!modal) return;
    ultimoFoco = document.activeElement;
    modal.classList.add("abierto");
    var primero = modal.querySelector("[data-foco-inicial], input:not([type=hidden]), select, textarea, button");
    if (primero) primero.focus();
  }

  function cerrarModal(modal) {
    if (!modal) return;
    modal.classList.remove("abierto");
    if (ultimoFoco && document.contains(ultimoFoco)) ultimoFoco.focus();
  }

  document.addEventListener("click", function (evento) {
    var abrir = evento.target.closest("[data-abrir-modal]");
    if (abrir) {
      abrirModal(document.getElementById(abrir.getAttribute("data-abrir-modal")));
      return;
    }
    var cerrar = evento.target.closest("[data-cerrar-modal]");
    if (cerrar) {
      cerrarModal(cerrar.closest(".modal-overlay"));
      return;
    }
    // Clic en el fondo oscuro (fuera de la tarjeta): tambien cierra.
    if (evento.target.classList.contains("modal-overlay")) {
      cerrarModal(evento.target);
      return;
    }
    var alerta = evento.target.closest("[data-cerrar-alerta]");
    if (alerta) alerta.closest(".alert").remove();
  });

  document.addEventListener("keydown", function (evento) {
    if (evento.key !== "Escape") return;
    var abiertos = document.querySelectorAll(".modal-overlay.abierto");
    if (abiertos.length) cerrarModal(abiertos[abiertos.length - 1]);
  });

  /* ---------- Confirmacion antes de eliminar ---------- */

  // Un formulario con data-confirmar no se envia de inmediato: primero
  // se muestra la ventana #modalConfirmar con su mensaje.
  //
  // SEGURIDAD: el mensaje se coloca con textContent, que lo inserta como
  // texto literal. Aunque el nombre de un proyecto contenga comillas o
  // etiquetas como <script>, se muestra tal cual y nunca se ejecuta.
  // (Antes se usaba onsubmit="return confirm('...nombre...')", donde el
  // nombre quedaba dentro de codigo JavaScript y podia inyectar codigo.)
  var modalConfirmar = document.getElementById("modalConfirmar");
  var formularioPendiente = null;

  document.addEventListener("submit", function (evento) {
    var formulario = evento.target;
    if (!modalConfirmar || !formulario.hasAttribute("data-confirmar")) return;
    evento.preventDefault();
    formularioPendiente = formulario;
    document.getElementById("confirmarMensaje").textContent = formulario.getAttribute("data-confirmar");
    var boton = formulario.getAttribute("data-confirmar-boton");
    document.getElementById("confirmarAceptar").textContent = boton || "Eliminar";
    // "No se puede deshacer" solo aplica a eliminar (desactivar si se revierte).
    document.getElementById("confirmarNota").hidden = Boolean(boton);
    abrirModal(modalConfirmar);
  });

  if (modalConfirmar) {
    document.getElementById("confirmarAceptar").addEventListener("click", function () {
      var formulario = formularioPendiente;
      formularioPendiente = null;
      // formulario.submit() envia sin volver a disparar el evento
      // "submit", asi que no se vuelve a pedir confirmacion.
      if (formulario) formulario.submit();
    });
  }

  /* ---------- Buscador y filtros de las tablas ---------- */

  // Solo filtran las filas que ya estan en pantalla; no consultan la
  // base de datos. Una tabla participa si tiene id="tabla-datos"; cada
  // fila puede declarar data-filtro-xxx y cada <select data-filtro="xxx">
  // filtra por ese atributo.
  var tabla = document.getElementById("tabla-datos");
  if (tabla) {
    var buscador = document.getElementById("buscador");
    var selects = document.querySelectorAll("select[data-filtro]");
    var contador = document.getElementById("contador-visibles");
    var filas = tabla.querySelectorAll("tbody tr[data-fila]");

    // Fila "sin resultados", creada una sola vez y oculta.
    var sinResultados = document.createElement("tr");
    var celda = document.createElement("td");
    celda.colSpan = tabla.querySelectorAll("thead th").length || 1;
    celda.className = "vacio";
    celda.textContent = "Ningún registro coincide con la búsqueda o los filtros.";
    sinResultados.appendChild(celda);
    sinResultados.hidden = true;
    if (filas.length) tabla.querySelector("tbody").appendChild(sinResultados);

    var aplicar = function () {
      var texto = buscador ? buscador.value.trim().toLowerCase() : "";
      var visibles = 0;
      filas.forEach(function (fila) {
        var ok = !texto || fila.textContent.toLowerCase().indexOf(texto) !== -1;
        selects.forEach(function (s) {
          if (s.value && fila.getAttribute("data-filtro-" + s.dataset.filtro) !== s.value) ok = false;
        });
        fila.style.display = ok ? "" : "none";
        if (ok) visibles++;
      });
      if (contador) contador.textContent = visibles;
      sinResultados.hidden = visibles > 0 || filas.length === 0;
    };
    if (buscador) buscador.addEventListener("input", aplicar);
    selects.forEach(function (s) { s.addEventListener("change", aplicar); });
  }
})();
