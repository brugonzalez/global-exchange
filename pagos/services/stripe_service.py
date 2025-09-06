import stripe
from django.conf import settings

class StripeService:
    """
    Servicio para interactuar con la API de Stripe.

    Métodos disponibles:
    - crear_customer(email, name): Crea un cliente en Stripe.
    - crear_metodo_pago(card_number, exp_month, exp_year, cvc): Crea un método de pago, en nuestro caso TC.
    - vincular_cliente_metodo_pago(payment_method_id, customer_id): Vincula un método de pago a un cliente.
    - crear_intento_metodo_pago(amount, currency, customer_id, payment_method_id): Crea y confirma un intento de pago.
    """

    def __init__(self):
        stripe.api_key = settings.STRIPE_CLAVE_SECRETA

    def crear_customer(self, email, name):
        return stripe.Customer.create(email=email, name=name)

    def crear_metodo_pago(self, card_number, exp_month, exp_year, cvc):
        return stripe.PaymentMethod.create(
            type="card",
            card={
                "number": card_number,
                "exp_month": exp_month,
                "exp_year": exp_year,
                "cvc": cvc,
            }
        )

    def vincular_cliente_metodo_pago(self, payment_method_id, customer_id):
        return stripe.PaymentMethod.attach(
            payment_method_id,
            customer=customer_id,
        )

    def crear_intento_metodo_pago(self, amount, currency, customer_id, payment_method_id):
        return stripe.PaymentIntent.create(
            amount=amount,
            currency=currency,
            customer=customer_id,
            payment_method=payment_method_id,
            confirm=True,
        )

    def crear_y_asociar_payment_method(self, stripe_token, customer_id):
        """
        Crea un PaymentMethod en Stripe a partir de un token y lo asocia a un customer.
        """
        pm = self.crear_metodo_pago_con_token(stripe_token)
        self.vincular_cliente_metodo_pago(pm.id, customer_id)
        return pm

    def crear_metodo_pago_con_token(self, stripe_token):
        """
        Crea un PaymentMethod usando un token recibido desde Stripe.js
        """
        return stripe.PaymentMethod.create(
            type="card",
            card={"token": stripe_token}
        )

    def datos_tarjeta(self, id_payment_method):
        """
        Obtiene los datos relevantes de una tarjeta a partir del ID del PaymentMethod.
        """
        pm = stripe.PaymentMethod.retrieve(id_payment_method)
        if pm.type == "card":
            return {
                "ultimos_digitos": pm.card.last4,
                "marca": pm.card.brand,
                "exp_mes": pm.card.exp_month,
                "exp_anio": pm.card.exp_year,
            }
        return {}