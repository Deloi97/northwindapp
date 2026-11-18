/* Interacciones comunes de Northwind Manager. */
document.addEventListener("DOMContentLoaded", () => {
    // Permite revisar la contraseña en la pantalla de acceso sin cambiar su valor.
    const passwordButton = document.getElementById("togglePassword");
    if (passwordButton) {
        passwordButton.addEventListener("click", () => {
            const passwordInput = document.getElementById("contrasena");
            const visible = passwordInput.type === "text";
            passwordInput.type = visible ? "password" : "text";
            passwordButton.innerHTML = `<i class="bi ${visible ? "bi-eye" : "bi-eye-slash"}"></i>`;
            passwordButton.setAttribute("aria-label", visible ? "Mostrar contraseña" : "Ocultar contraseña");
            passwordButton.title = visible ? "Mostrar contraseña" : "Ocultar contraseña";
        });
    }

    // Advierte si Windows está escribiendo en mayúsculas. No cambiamos el valor
    // de la contraseña porque sus mayúsculas y minúsculas deben conservarse.
    const capsLockWarning = document.getElementById("capsLockWarning");
    const loginFields = [
        document.getElementById("usuario"),
        document.getElementById("contrasena"),
    ].filter(Boolean);
    if (capsLockWarning && loginFields.length) {
        const updateCapsLockWarning = (event) => {
            const active = event.getModifierState?.("CapsLock") ?? false;
            capsLockWarning.classList.toggle("d-none", !active);
        };
        loginFields.forEach((field) => {
            field.addEventListener("keydown", updateCapsLockWarning);
            field.addEventListener("keyup", updateCapsLockWarning);
        });
    }

    // Los modales de edición se llenan con el registro que ya llegó desde SQL Server.
    document.querySelectorAll(".modal form[data-create-action]").forEach((form) => {
        const modal = form.closest(".modal");
        const title = modal.querySelector(".modal-title");
        const createTitle = title.textContent.trim();
        const editTitle = createTitle.replace("Agregar", "Editar");

        // Bootstrap entrega en relatedTarget el botón que abrió el modal. Si el
        // botón es de edición se cargan sus datos; si no, queda como formulario nuevo.
        modal.addEventListener("show.bs.modal", (event) => {
            const trigger = event.relatedTarget;
            form.reset();
            form.classList.remove("was-validated");
            form.action = form.dataset.createAction;
            title.textContent = createTitle;

            const createOnly = modal.querySelector(".create-only");
            if (createOnly) {
                createOnly.classList.remove("d-none");
                const idInput = createOnly.querySelector("input");
                if (idInput) idInput.required = true;
            }

            if (!trigger || !trigger.classList.contains("edit-button")) return;

            // data-record contiene el registro convertido a JSON por Jinja.
            const record = JSON.parse(trigger.dataset.record);
            form.action = trigger.dataset.action;
            title.textContent = editTitle;
            if (createOnly) {
                createOnly.classList.add("d-none");
                const idInput = createOnly.querySelector("input");
                if (idInput) idInput.required = false;
            }

            // data-field relaciona cada control HTML con una columna de SQL Server.
            form.querySelectorAll("[data-field]").forEach((field) => {
                const value = record[field.dataset.field];
                if (field.type === "checkbox") {
                    field.checked = Boolean(value);
                } else {
                    field.value = value ?? "";
                }
            });
        });
    });

    // Un solo modal confirma cualquier eliminación y recibe su URL desde el botón.
    const deleteModal = document.getElementById("deleteModal");
    if (deleteModal) {
        deleteModal.addEventListener("show.bs.modal", (event) => {
            const button = event.relatedTarget;
            deleteModal.querySelector("#deleteForm").action = button.dataset.action;
            const name = button.dataset.name || "este registro";
            deleteModal.querySelector("#deleteMessage").textContent =
                `Se eliminará “${name}”. Esta acción no se puede deshacer.`;
        });
    }

    // Validación visual de Bootstrap antes de enviar formularios. La validación
    // del servidor en app.py se mantiene porque JavaScript puede desactivarse.
    document.querySelectorAll("input, select, textarea").forEach((field) => {
        // Los mensajes nativos cambian con el idioma del navegador. Definirlos
        // aquí garantiza que las alertas de validación siempre estén en español.
        field.addEventListener("invalid", () => {
            if (field.validity.valueMissing) {
                field.setCustomValidity("Completa este campo obligatorio.");
            } else if (field.validity.typeMismatch) {
                field.setCustomValidity("Escribe un valor con el formato correcto.");
            } else if (field.validity.rangeUnderflow) {
                field.setCustomValidity(`El valor mínimo permitido es ${field.min}.`);
            } else if (field.validity.tooShort) {
                field.setCustomValidity(`Escribe al menos ${field.minLength} caracteres.`);
            } else if (field.validity.tooLong) {
                field.setCustomValidity(`Escribe como máximo ${field.maxLength} caracteres.`);
            } else {
                field.setCustomValidity("Revisa el valor de este campo.");
            }
        });
        field.addEventListener("input", () => field.setCustomValidity(""));
        field.addEventListener("change", () => field.setCustomValidity(""));
    });

    document.querySelectorAll("form").forEach((form) => {
        form.addEventListener("submit", (event) => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add("was-validated");
        });
    });

    // El detalle del pedido se solicita solo cuando el usuario pulsa Consultar.
    // fetch recibe JSON desde /api/pedidos/<id> y lo dibuja dentro del modal.
    const orderModal = document.getElementById("orderModal");
    if (orderModal) {
        orderModal.addEventListener("show.bs.modal", async (event) => {
            const button = event.relatedTarget;
            const body = orderModal.querySelector("#orderDetailBody");
            const title = orderModal.querySelector(".modal-title");
            title.textContent = "Cargando...";
            body.innerHTML = '<div class="loading-state"><div class="spinner-border text-primary"></div><span>Consultando SQL Server...</span></div>';

            try {
                const response = await fetch(button.dataset.url, {headers: {Accept: "application/json"}});
                const data = await response.json();
                if (!response.ok) throw new Error(data.error || "No se pudo consultar el pedido.");
                title.textContent = `Pedido #${data.OrderID}`;
                body.innerHTML = renderOrder(data);
            } catch (error) {
                body.innerHTML = `<div class="alert alert-danger mb-0"><i class="bi bi-x-circle me-2"></i>${escapeHtml(error.message)}</div>`;
            }
        });
    }
});

function escapeHtml(value) {
    // Colocar primero el texto en un elemento evita inyectar HTML proveniente de
    // nombres o direcciones guardados en la base de datos.
    const element = document.createElement("div");
    element.textContent = value ?? "";
    return element.innerHTML;
}

function formatDate(value) {
    // SQL/JSON envía YYYY-MM-DD; la interfaz en español muestra DD/MM/YYYY.
    if (!value) return "—";
    const parts = value.slice(0, 10).split("-");
    return parts.length === 3 ? `${parts[2]}/${parts[1]}/${parts[0]}` : value;
}

function formatMoney(value) {
    // Intl.NumberFormat agrega separadores y dos decimales de forma consistente.
    return new Intl.NumberFormat("es-MX", {
        style: "currency", currency: "USD", minimumFractionDigits: 2
    }).format(Number(value || 0));
}

function renderOrder(order) {
    // Construye el contenido del modal con datos ya validados/escapados. Cada
    // subtotal viene calculado por SQL con precio, cantidad y descuento.
    const destination = [order.ShipAddress, order.ShipCity, order.ShipRegion, order.ShipPostalCode, order.ShipCountry]
        .filter(Boolean).map(escapeHtml).join(", ") || "Sin dirección registrada";
    const rows = order.detalles.map((item) => `
        <tr>
            <td><strong>${escapeHtml(item.ProductName)}</strong></td>
            <td>${formatMoney(item.UnitPrice)}</td>
            <td>${item.Quantity}</td>
            <td>${Math.round(Number(item.Discount || 0) * 100)}%</td>
            <td class="text-end fw-bold">${formatMoney(item.LineTotal)}</td>
        </tr>`).join("");

    return `
        <div class="order-summary-grid">
            <div><span>Cliente</span><strong>${escapeHtml(order.CompanyName || "Sin cliente")}</strong><small>${escapeHtml(order.ContactName || "")}</small></div>
            <div><span>Fecha del pedido</span><strong>${formatDate(order.OrderDate)}</strong><small>Requerido: ${formatDate(order.RequiredDate)}</small></div>
            <div><span>Fecha de envío</span><strong>${formatDate(order.ShippedDate)}</strong><small>${order.ShippedDate ? "Pedido enviado" : "Pendiente de envío"}</small></div>
        </div>
        <div class="shipping-box"><i class="bi bi-geo-alt"></i><div><span>Dirección de entrega</span><strong>${escapeHtml(order.ShipName || "")}</strong><p>${destination}</p></div></div>
        <div class="table-responsive">
            <table class="table app-table order-lines align-middle mb-0">
                <thead><tr><th>Producto</th><th>Precio</th><th>Cantidad</th><th>Descuento</th><th class="text-end">Subtotal</th></tr></thead>
                <tbody>${rows || '<tr><td colspan="5" class="text-center py-4">Sin productos.</td></tr>'}</tbody>
                <tfoot><tr><td colspan="4" class="text-end">Total del pedido</td><td class="text-end">${formatMoney(order.total)}</td></tr></tfoot>
            </table>
        </div>`;
}
