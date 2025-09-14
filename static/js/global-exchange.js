// Funcionalidad JavaScript de Global Exchange

// Funcionalidad simple tipo jQuery para compatibilidad
function $(selector) {
    if (typeof selector === 'string') {
        return {
            elementos: document.querySelectorAll(selector),
            
            each: function(callback) {
                this.elementos.forEach(callback);
                return this;
            },
            
            on: function(evento, callback) {
                this.elementos.forEach(el => el.addEventListener(evento, callback));
                return this;
            },
            
            find: function(selector) {
                const encontrados = [];
                this.elementos.forEach(el => {
                    encontrados.push(...el.querySelectorAll(selector));
                });
                return { elementos: encontrados, ...$(encontrados) };
            },
            
            text: function(valor) {
                if (valor !== undefined) {
                    this.elementos.forEach(el => el.textContent = valor);
                    return this;
                } else {
                    return this.elementos[0]?.textContent || '';
                }
            },
            
            val: function(valor) {
                if (valor !== undefined) {
                    this.elementos.forEach(el => el.value = valor);
                    return this;
                } else {
                    return this.elementos[0]?.value || '';
                }
            },
            
            show: function() {
                this.elementos.forEach(el => el.style.display = '');
                return this;
            },
            
            hide: function() {
                this.elementos.forEach(el => el.style.display = 'none');
                return this;
            },
            
            length: this.elementos?.length || 0
        };
    }
    
    if (selector === document) {
        return {
            ready: function(callback) {
                if (document.readyState === 'loading') {
                    document.addEventListener('DOMContentLoaded', callback);
                } else {
                    callback();
                }
            }
        };
    }
    
    return { elementos: [] };
}

// Funcionalidad AJAX
function ajax(opciones) {
    const xhr = new XMLHttpRequest();
    xhr.open(opciones.method || 'GET', opciones.url);
    
    // Establecer token CSRF para Django
    const csrftoken = obtenerCookie('csrftoken');
    if (csrftoken) {
        xhr.setRequestHeader('X-CSRFToken', csrftoken);
    }
    
    if (opciones.method === 'POST') {
        xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
    }
    
    xhr.onreadystatechange = function() {
        if (xhr.readyState === 4) {
            if (xhr.status >= 200 && xhr.status < 300) {
                try {
                    const datos = JSON.parse(xhr.responseText);
                    if (opciones.success) opciones.success(datos);
                } catch (e) {
                    if (opciones.success) opciones.success(xhr.responseText);
                }
            } else {
                if (opciones.error) opciones.error(xhr);
            }
        }
    };
    
    xhr.send(opciones.data || null);
}

// Funciones de utilidad
function obtenerCookie(nombre) {
    let valorCookie = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, nombre.length + 1) === (nombre + '=')) {
                valorCookie = decodeURIComponent(cookie.substring(nombre.length + 1));
                break;
            }
        }
    }
    return valorCookie;
}

// Formatear número para visualización de moneda
function formatearMoneda(monto, decimales = 4) {
    return parseFloat(monto).toLocaleString('es-AR', {
        minimumFractionDigits: decimales,
        maximumFractionDigits: decimales
    });
}

// Formatear valor decimal para parámetros de moneda según precisión
function formatearValorParametroMoneda(valor, precision) {
    if (valor === null || valor === undefined || valor === '') {
        return '';
    }
    
    // Convertir a número y aplicar la precisión
    const numero = parseFloat(valor);
    if (isNaN(numero)) {
        return '';
    }
    
    // Formatear con la precisión especificada, evitando notación científica
    return numero.toFixed(precision);
}

// Obtener el step apropiado para un campo según la precisión decimal
function obtenerStepSegunPrecision(precision) {
    if (precision <= 0) {
        return '1';
    }
    // Crear step como 0.0...01 con precision decimales
    return '0.' + '0'.repeat(precision - 1) + '1';
}

// Aplicar formato de precisión decimal a los campos de parámetros de moneda
function aplicarPrecisionDecimalCampos(precision) {
    // Campos que siempre son enteros (sin decimales)
    const camposEnteros = [
        'id_denominacion_minima', 
        'id_stock_inicial'
    ];
    
    // Campos que usan la precisión definida
    const camposPrecision = [
        'id_precio_base_inicial'
    ];
    
    // Configurar campos enteros
    camposEnteros.forEach(function(campoId) {
        const campo = document.getElementById(campoId);
        if (campo) {
            campo.setAttribute('step', '1');
            
            // Ajustar min según el campo
            if (campoId === 'id_denominacion_minima') {
                campo.setAttribute('min', '1');  // Denominación mínima debe ser >= 1
            } else {
                campo.setAttribute('min', '0');  // Stock inicial puede ser 0
            }
            
            // Reformatear valor actual como entero
            const valorActual = campo.value;
            if (valorActual && valorActual !== '') {
                const valorEntero = Math.floor(parseFloat(valorActual) || 0);
                campo.value = valorEntero.toString();
            }
        }
    });
    
    // Configurar campos con precisión
    const step = obtenerStepSegunPrecision(precision);
    camposPrecision.forEach(function(campoId) {
        const campo = document.getElementById(campoId);
        if (campo) {
            campo.setAttribute('step', step);
            
            if (precision <= 0) {
                campo.setAttribute('min', '1');
            } else {
                campo.setAttribute('min', step);
            }
            
            // Reformatear el valor actual si existe
            const valorActual = campo.value;
            if (valorActual && valorActual !== '') {
                const valorFormateado = formatearValorParametroMoneda(valorActual, precision);
                campo.value = valorFormateado;
            }
        }
    });
}

// Funcionalidad de actualización de tasas
function refrescarTasas() {
    const urlApi = document.querySelector('[data-rates-api]')?.getAttribute('data-rates-api');
    if (!urlApi) return;
    
    ajax({
        url: urlApi,
        method: 'GET',
        success: function(datos) {
            if (datos.tasas) {
                datos.tasas.forEach(function(tasa) {
                    const tarjetaTasa = document.querySelector(`[data-currency="${tasa.moneda}"]`);
                    if (tarjetaTasa) {
                        const elTasaCompra = tarjetaTasa.querySelector('.tasa-compra');
                        const elTasaVenta = tarjetaTasa.querySelector('.tasa-venta');
                        const elUltimaActualizacion = tarjetaTasa.querySelector('.ultima-actualizacion');
                        
                        if (elTasaCompra) elTasaCompra.textContent = formatearMoneda(tasa.tasa_compra);
                        if (elTasaVenta) elTasaVenta.textContent = formatearMoneda(tasa.tasa_venta);
                        if (elUltimaActualizacion) {
                            const hora = new Date(tasa.ultima_actualizacion).toLocaleTimeString('es-AR');
                            elUltimaActualizacion.textContent = `Actualizado: ${hora}`;
                        }
                    }
                });
            }
        },
        error: function(xhr) {
            console.error('Error al refrescar las tasas:', xhr.statusText);
        }
    });
}

// Funcionalidad de simulación
function simularConversion() {
    const formulario = document.querySelector('#formulario-simulacion');
    if (!formulario) return;
    
    const datosFormulario = new FormData(formulario);
    const datos = new URLSearchParams();
    
    for (let [clave, valor] of datosFormulario.entries()) {
        datos.append(clave, valor);
    }
    
    const urlApi = formulario.getAttribute('data-api-url');
    if (!urlApi) return;
    
    ajax({
        url: urlApi,
        method: 'POST',
        data: datos.toString(),
        success: function(respuesta) {
            const divResultado = document.querySelector('#resultado-simulacion');
            if (divResultado && respuesta.success) {
                const resultado = respuesta.resultado;
                divResultado.innerHTML = `
                    <div class="alert alert-success">
                        <h5>Resultado de la Simulación</h5>
                        <p><strong>Operación:</strong> ${resultado.tipo_operacion}</p>
                        <p><strong>Monto origen:</strong> ${formatearMoneda(resultado.monto_origen)} ${resultado.moneda_origen}</p>
                        <p><strong>Monto destino:</strong> ${formatearMoneda(resultado.monto_destino)} ${resultado.moneda_destino}</p>
                        <p><strong>Tasa aplicada:</strong> ${formatearMoneda(resultado.tasa_cambio)}</p>
                        ${resultado.monto_comision > 0 ? `<p><strong>Comisión:</strong> ${formatearMoneda(resultado.monto_comision)} ${resultado.moneda_origen}</p>` : ''}
                    </div>
                `;
                divResultado.style.display = 'block';
            } else {
                const divResultado = document.querySelector('#resultado-simulacion');
                if (divResultado) {
                    divResultado.innerHTML = `
                        <div class="alert alert-danger">
                            <p>Error en la simulación: ${respuesta.error || 'Error desconocido'}</p>
                        </div>
                    `;
                    divResultado.style.display = 'block';
                }
            }
        },
        error: function(xhr) {
            const divResultado = document.querySelector('#resultado-simulacion');
            if (divResultado) {
                divResultado.innerHTML = `
                    <div class="alert alert-danger">
                        <p>Error de conexión. Por favor, intente nuevamente.</p>
                    </div>
                `;
                divResultado.style.display = 'block';
            }
        }
    });
}

// Descartar alertas automáticamente
function autoDescartarAlertas() {
    const alertas = document.querySelectorAll('.alert[data-auto-dismiss]');
    alertas.forEach(alerta => {
        const demora = parseInt(alerta.getAttribute('data-auto-dismiss')) || 5000;
        setTimeout(() => {
            alerta.style.opacity = '0';
            setTimeout(() => alerta.remove(), 300);
        }, demora);
    });
}

// Inicializar cuando el DOM esté listo
$(document).ready(function() {
    // Descartar alertas automáticamente
    autoDescartarAlertas();
    
    // Manejador del formulario de simulación
    const botonSimular = document.querySelector('#boton-simular');
    if (botonSimular) {
        botonSimular.addEventListener('click', function(e) {
            e.preventDefault();
            simularConversion();
        });
    }
    
    // Funcionalidad del botón de cierre para las alertas
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('btn-close')) {
            const alerta = e.target.closest('.alert');
            if (alerta) {
                alerta.style.opacity = '0';
                setTimeout(() => alerta.remove(), 300);
            }
        }
    });
    
    // Alternar menú móvil
    const alternadorNav = document.querySelector('.navbar-toggler');
    const colapsoNav = document.querySelector('.navbar-collapse');
    if (alternadorNav && colapsoNav) {
        alternadorNav.addEventListener('click', function() {
            colapsoNav.style.display = colapsoNav.style.display === 'block' ? 'none' : 'block';
        });
    }
});

// Funciones globales para uso externo
window.IG = {
    refrescarTasas: refrescarTasas,
    simularConversion: simularConversion,
    formatearMoneda: formatearMoneda,
    formatearValorParametroMoneda: formatearValorParametroMoneda,
    obtenerStepSegunPrecision: obtenerStepSegunPrecision,
    aplicarPrecisionDecimalCampos: aplicarPrecisionDecimalCampos,
    ajax: ajax,
    obtenerCookie: obtenerCookie,
    crearGrafico: crearGrafico
};

// Implementación simple de gráficos usando Canvas
function crearGrafico(idCanvas, datos, opciones = {}) {
    const canvas = document.getElementById(idCanvas);
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    const ancho = canvas.width = canvas.offsetWidth;
    const alto = canvas.height = canvas.offsetHeight;
    
    // Limpiar canvas
    ctx.clearRect(0, 0, ancho, alto);
    
    // Opciones predeterminadas
    const opts = {
        type: opciones.type || 'line',
        title: opciones.title || '',
        yAxisLabel: opciones.yAxisLabel || '',
        xAxisLabel: opciones.xAxisLabel || '',
        colors: opciones.colors || ['#007bff', '#28a745'],
        backgroundColor: opciones.backgroundColor || 'white',
        gridColor: opciones.gridColor || '#e0e0e0',
        textColor: opciones.textColor || '#333',
        padding: opciones.padding || 60,
        ...opciones
    };
    
    if (!datos.labels || !datos.datasets || datos.datasets.length === 0) {
        // Mostrar mensaje "No hay datos"
        ctx.fillStyle = opts.textColor;
        ctx.font = '16px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('No hay datos disponibles', ancho/2, alto/2);
        return;
    }
    
    // Calcular área del gráfico
    const areaGrafico = {
        left: opts.padding,
        top: opts.padding,
        right: ancho - opts.padding,
        bottom: alto - opts.padding,
        width: ancho - (opts.padding * 2),
        height: alto - (opts.padding * 2)
    };
    
    // Encontrar valores mínimos/máximos
    let minY = Infinity, maxY = -Infinity;
    datos.datasets.forEach(dataset => {
        dataset.data.forEach(valor => {
            if (valor < minY) minY = valor;
            if (valor > maxY) maxY = valor;
        });
    });
    
    // Añadir un poco de relleno al rango Y
    const rangoY = maxY - minY;
    minY -= rangoY * 0.1;
    maxY += rangoY * 0.1;
    
    // Funciones de ayuda
    function obtenerX(indice) {
        return areaGrafico.left + (indice / (datos.labels.length - 1)) * areaGrafico.width;
    }
    
    function obtenerY(valor) {
        return areaGrafico.bottom - ((valor - minY) / (maxY - minY)) * areaGrafico.height;
    }
    
    // Dibujar fondo
    ctx.fillStyle = opts.backgroundColor;
    ctx.fillRect(0, 0, ancho, alto);
    
    // Dibujar rejilla
    ctx.strokeStyle = opts.gridColor;
    ctx.lineWidth = 1;
    
    // Líneas de rejilla verticales
    for (let i = 0; i < datos.labels.length; i += Math.ceil(datos.labels.length / 8)) {
        const x = obtenerX(i);
        ctx.beginPath();
        ctx.moveTo(x, areaGrafico.top);
        ctx.lineTo(x, areaGrafico.bottom);
        ctx.stroke();
    }
    
    // Líneas de rejilla horizontales
    const pasosY = 5;
    for (let i = 0; i <= pasosY; i++) {
        const valor = minY + (maxY - minY) * (i / pasosY);
        const y = obtenerY(valor);
        ctx.beginPath();
        ctx.moveTo(areaGrafico.left, y);
        ctx.lineTo(areaGrafico.right, y);
        ctx.stroke();
    }
    
    // Dibujar etiquetas del eje Y
    ctx.fillStyle = opts.textColor;
    ctx.font = '12px Arial';
    ctx.textAlign = 'right';
    for (let i = 0; i <= pasosY; i++) {
        const valor = minY + (maxY - minY) * (i / pasosY);
        const y = obtenerY(valor);
        ctx.fillText(valor.toFixed(0), areaGrafico.left - 10, y + 4);
    }
    
    // Dibujar etiquetas del eje X
    ctx.textAlign = 'center';
    for (let j = datos.labels.length - 1; j >= 0; j -= Math.ceil(datos.labels.length / 8)) {
        const x = obtenerX(j);
        ctx.fillText(datos.labels[j], x, areaGrafico.bottom + 20);
    }
    
    // Dibujar título
    if (opts.title) {
        ctx.fillStyle = opts.textColor;
        ctx.font = 'bold 16px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(opts.title, ancho/2, 30);
    }
    
    // Dibujar conjuntos de datos
    datos.datasets.forEach((dataset, indiceDataset) => {
        const color = opts.colors[indiceDataset % opts.colors.length];
        
        if (opts.type === 'line') {
            // Dibujar línea
            ctx.strokeStyle = color;
            ctx.lineWidth = 2;
            ctx.beginPath();
            
            dataset.data.forEach((valor, indice) => {
                const x = obtenerX(indice);
                const y = obtenerY(valor);
                
                if (indice === 0) {
                    ctx.moveTo(x, y);
                } else {
                    ctx.lineTo(x, y);
                }
            });
            
            ctx.stroke();
            
            // Dibujar puntos
            ctx.fillStyle = color;
            dataset.data.forEach((valor, indice) => {
                const x = obtenerX(indice);
                const y = obtenerY(valor);
                ctx.beginPath();
                ctx.arc(x, y, 3, 0, Math.PI * 2);
                ctx.fill();
            });
        }
    });
    
    // Dibujar leyenda
    if (datos.datasets.length > 1) {
        const leyendaY = areaGrafico.bottom + 40;
        let leyendaX = areaGrafico.left;
        
        datos.datasets.forEach((dataset, indice) => {
            const color = opts.colors[indice % opts.colors.length];
            
            // Caja de color de la leyenda
            ctx.fillStyle = color;
            ctx.fillRect(leyendaX, leyendaY, 15, 15);
            
            // Texto de la leyenda
            ctx.fillStyle = opts.textColor;
            ctx.font = '12px Arial';
            ctx.textAlign = 'left';
            ctx.fillText(dataset.label || `Conjunto de datos ${indice + 1}`, leyendaX + 20, leyendaY + 12);
            
            leyendaX += 150;
        });
    }
}

// =================================
// AUTOCOMPLETADO DE SÍMBOLOS DE MONEDA
// =================================

/**
 * Mapeo de códigos ISO de moneda a sus símbolos
 */
const MAPEO_SIMBOLOS_MONEDA = {
    // Monedas principales
    'USD': '$',        // Dólar Estadounidense
    'EUR': '€',        // Euro
    'GBP': '£',        // Libra Esterlina
    'JPY': '¥',        // Yen Japonés
    'CHF': '₣',        // Franco Suizo
    'CAD': 'C$',       // Dólar Canadiense
    'AUD': 'A$',       // Dólar Australiano
    'CNY': '¥',        // Yuan Chino
    'INR': '₹',        // Rupia India
    'KRW': '₩',        // Won Surcoreano
    'SEK': 'kr',       // Corona Sueca
    'NOK': 'kr',       // Corona Noruega
    'DKK': 'kr',       // Corona Danesa
    'PLN': 'zł',       // Zloty Polaco
    'RUB': '₽',        // Rublo Ruso
    'TRY': '₺',        // Lira Turca
    'ZAR': 'R',        // Rand Sudafricano
    'SGD': 'S$',       // Dólar de Singapur
    'HKD': 'HK$',      // Dólar de Hong Kong
    'NZD': 'NZ$',      // Dólar Neozelandés
    'ILS': '₪',        // Shekel Israelí
    'THB': '฿',        // Baht Tailandés
    'MYR': 'RM',       // Ringgit Malayo
    'PHP': '₱',        // Peso Filipino
    'TWD': 'NT$',      // Dólar Taiwanés
    
    // Monedas de América Latina
    'ARS': '$',        // Peso Argentino
    'BRL': 'R$',       // Real Brasileño
    'CLP': '$',        // Peso Chileno
    'COP': '$',        // Peso Colombiano
    'PEN': 'S/',       // Nuevo Sol Peruano
    'UYU': '$',        // Peso Uruguayo
    'PYG': '₲',        // Guaraní Paraguayo
    'BOB': 'Bs',       // Boliviano
    'VES': 'Bs',       // Bolívar Venezolano
    'CRC': '₡',        // Colón Costarricense
    'GTQ': 'Q',        // Quetzal Guatemalteco
    'HNL': 'L',        // Lempira Hondureño
    'NIO': 'C$',       // Córdoba Nicaragüense
    'PAB': 'B/.',      // Balboa Panameño
    'DOP': 'RD$',      // Peso Dominicano
    'JMD': 'J$',       // Dólar Jamaiquino
    'TTD': 'TT$',      // Dólar de Trinidad y Tobago
    'BBD': 'Bds$',     // Dólar de Barbados
    'XCD': 'EC$',      // Dólar del Caribe Oriental
    'AWG': 'ƒ',        // Florín Arubeño
    'MXN': '$',        // Peso Mexicano
    'CUP': '$',        // Peso Cubano
    'HTG': 'G',        // Gourde Haitiano
    
    // Monedas de Europa
    'CZK': 'Kč',       // Corona Checa
    'HUF': 'Ft',       // Forint Húngaro
    'RON': 'lei',      // Leu Rumano
    'BGN': 'лв',       // Lev Búlgaro
    'HRK': 'kn',       // Kuna Croata
    'ISK': 'kr',       // Corona Islandesa
    'UAH': '₴',        // Grivna Ucraniana
    'BYN': 'Br',       // Rublo Bielorruso
    'MKD': 'ден',      // Denar Macedonio
    'RSD': 'дин',      // Dinar Serbio
    'BAM': 'KM',       // Marco Convertible de Bosnia
    'ALL': 'L',        // Lek Albanés
    'MDL': 'L',        // Leu Moldavo
    'GEL': '₾',        // Lari Georgiano
    'AMD': '֏',        // Dram Armenio
    'AZN': '₼',        // Manat Azerbaiyano
    
    // Monedas de África
    'NGN': '₦',        // Naira Nigeriana
    'EGP': '£',        // Libra Egipcia
    'KES': 'KSh',      // Chelín Keniano
    'GHS': '₵',        // Cedi Ghanés
    'UGX': 'USh',      // Chelín Ugandés
    'TZS': 'TSh',      // Chelín Tanzano
    'ETB': 'Br',       // Birr Etíope
    'MAD': 'DH',       // Dirham Marroquí
    'TND': 'د.ت',      // Dinar Tunecino
    'DZD': 'د.ج',      // Dinar Argelino
    'XOF': 'CFA',      // Franco CFA de África Occidental
    'XAF': 'FCFA',     // Franco CFA de África Central
    'BWP': 'P',        // Pula de Botsuana
    'NAD': 'N$',       // Dólar Namibio
    'SZL': 'L',        // Lilangeni de Suazilandia
    'LSL': 'L',        // Loti de Lesoto
    'MWK': 'MK',       // Kwacha Malauí
    'ZMW': 'ZK',       // Kwacha Zambiano
    'MZN': 'MT',       // Metical Mozambiqueño
    'AOA': 'Kz',       // Kwanza Angoleño
    
    // Monedas de Asia
    'SAR': '﷼',        // Riyal Saudí
    'AED': 'د.إ',       // Dirham de EAU
    'QAR': '﷼',        // Riyal Qatarí
    'KWD': 'د.ك',       // Dinar Kuwaití
    'BHD': '.د.ب',      // Dinar Bahreiní
    'OMR': '﷼',        // Rial Omaní
    'JOD': 'د.ا',       // Dinar Jordano
    'LBP': '£',        // Libra Libanesa
    'SYP': '£',        // Libra Siria
    'IQD': 'ع.د',       // Dinar Iraquí
    'IRR': '﷼',        // Rial Iraní
    'AFN': '؋',        // Afgani
    'PKR': '₨',        // Rupia Pakistaní
    'LKR': '₨',        // Rupia de Sri Lanka
    'BDT': '৳',        // Taka de Bangladesh
    'NPR': '₨',        // Rupia Nepalí
    'BTN': 'Nu.',      // Ngultrum Butanés
    'MVR': '.ރ',       // Rufiyaa Maldiva
    'MMK': 'K',        // Kyat Birmano
    'LAK': '₭',        // Kip Laosiano
    'KHR': '៛',        // Riel Camboyano
    'VND': '₫',        // Dong Vietnamita
    'IDR': 'Rp',       // Rupia Indonesia
    'BND': 'B$',       // Dólar de Brunéi
    'KZT': '₸',        // Tenge Kazajo
    'KGS': 'лв',       // Som Kirguís
    'TJS': 'SM',       // Somoni Tayiko
    'TMT': 'T',        // Manat Turkmeno
    'UZS': 'лв',       // Som Uzbeko
    'MNT': '₮',        // Tugrik Mongol
    'KPW': '₩',        // Won Norcoreano
    
    // Monedas de Oceanía
    'FJD': 'FJ$',      // Dólar Fiyiano
    'TOP': 'T$',       // Pa'anga Tongano
    'WST': 'WS$',      // Tala Samoano
    'VUV': 'VT',       // Vatu de Vanuatu
    'SBD': 'SI$',      // Dólar de las Islas Salomón
    'PGK': 'K',        // Kina de Papúa Nueva Guinea
    'XPF': '₣',        // Franco CFP
    
    // Criptomonedas principales
    'BTC': '₿',        // Bitcoin
    'ETH': 'Ξ',        // Ethereum
    'LTC': 'Ł',        // Litecoin
    'BCH': '₿',        // Bitcoin Cash
    'XRP': 'XRP',      // Ripple
    'ADA': '₳',        // Cardano
    'DOT': '●',        // Polkadot
    'DOGE': 'Ð',       // Dogecoin
};

/**
 * Autocompletar símbolo de moneda basado en el código ingresado
 * @param {string} codigo - Código de moneda (ej: "USD", "EUR")
 * @returns {string} - Símbolo correspondiente o cadena vacía si no se encuentra
 */
function autocompletarSimboloMoneda(codigo) {
    if (!codigo || typeof codigo !== 'string') {
        return '';
    }
    
    // Convertir a mayúsculas y limpiar espacios
    const codigoLimpio = codigo.trim().toUpperCase();
    
    // Buscar en el mapeo
    return MAPEO_SIMBOLOS_MONEDA[codigoLimpio] || '';
}

/**
 * Inicializar autocompletado de símbolos para formularios de moneda
 */
function inicializarAutocompletadoSimbolos() {
    // Buscar el campo de código de moneda
    const campoCodigo = document.querySelector('input[name="codigo"]');
    const campoSimbolo = document.querySelector('input[name="simbolo"]');
    
    if (!campoCodigo || !campoSimbolo) {
        return; // No hay formulario de moneda en esta página
    }
    
    // Agregar evento de input al campo código
    campoCodigo.addEventListener('input', function(e) {
        const codigo = e.target.value;
        const simbolo = autocompletarSimboloMoneda(codigo);
        
        // Solo autocompletar si el campo símbolo está vacío o si el usuario lo prefiere
        if (simbolo && (!campoSimbolo.value || campoSimbolo.dataset.autocompletado === 'true')) {
            campoSimbolo.value = simbolo;
            campoSimbolo.dataset.autocompletado = 'true';
            
            // Mostrar un pequeño indicador visual
            campoSimbolo.style.backgroundColor = '#e8f5e8';
            setTimeout(() => {
                campoSimbolo.style.backgroundColor = '';
            }, 1000);
        }
    });
    
    // Manejar cuando el usuario modifica manualmente el símbolo
    campoSimbolo.addEventListener('input', function() {
        // Marcar que el usuario ha modificado manualmente el símbolo
        campoSimbolo.dataset.autocompletado = 'false';
    });
    
    // Agregar tooltip con información
    if (campoCodigo.parentNode) {
        const tooltipTexto = campoCodigo.parentNode.querySelector('.form-text');
        if (tooltipTexto) {
            tooltipTexto.innerHTML += '<br><small class="text-info"><i class="fas fa-magic me-1"></i>El símbolo se autocompletará automáticamente para códigos ISO conocidos.</small>';
        }
    }
}

// Exponer funciones al objeto global IG
if (typeof IG !== 'undefined') {
    IG.autocompletarSimboloMoneda = autocompletarSimboloMoneda;
    IG.inicializarAutocompletadoSimbolos = inicializarAutocompletadoSimbolos;
}

// Auto-inicializar cuando el DOM esté listo
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', inicializarAutocompletadoSimbolos);
} else {
    inicializarAutocompletadoSimbolos();
}