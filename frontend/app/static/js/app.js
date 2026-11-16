// Métodos auxiliares para la interfaz Web

document.addEventListener('DOMContentLoaded', () => {
    const input = document.getElementById('id_factura');

    // Normaliza el ID de factura a mayúsculas y sin espacios
    input.addEventListener('input', () => {
        input.value = input.value.toUpperCase().replace(/\s+/g, '');
    });

    // Oculta los mensajes de error después de unos segundos
    const alerta = document.querySelector('.alert');
    if (alerta) {
        setTimeout(() => alerta.remove(), 6000);
    }
});
