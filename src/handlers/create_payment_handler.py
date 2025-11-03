"""
Handler: create payment transaction
SPDX - License - Identifier: LGPL - 3.0 - or -later
Auteurs : Gabriel C. Ullmann, Fabio Petrillo, 2025
"""
import config
import requests
from logger import Logger
from handlers.handler import Handler
from order_saga_state import OrderSagaState

class CreatePaymentHandler(Handler):
    """ Handle the creation of a payment transaction for a given order. Trigger rollback of previous steps in case of failure. """

    def __init__(self, order_id, order_data):
        """ Constructor method """
        self.order_id = order_id
        self.order_data = order_data
        self.total_amount = 0
        super().__init__()

    def run(self):
        """Call payment microservice to generate payment transaction"""
        try:
            # Récupérer le montant total de la commande
            response = requests.get(f'{config.API_GATEWAY_URL}/store-manager-api/orders/{self.order_id}')
            if response.ok:
                data = response.json()
                self.total_amount = data.get("total_amount", 0)
            else:
                text = response.json()
                self.logger.error(f"Erreur {response.status_code} lors de la récupération du montant total : {text}")
                return OrderSagaState.INCREASING_STOCK

            # Créer une transaction de paiement
            response = requests.post(f'{config.API_GATEWAY_URL}/store-manager-api/payments',
                json={
                    "order_id": self.order_id,
                    "amount": self.total_amount,
                    "payment_method": self.order_data.get("payment_method", "credit_card")
                },
                headers={'Content-Type': 'application/json'}
            )
            if response.ok:
                self.logger.debug("La création d'une transaction de paiement a réussi")
                return OrderSagaState.COMPLETED
            else:
                text = response.json()
                self.logger.error(f"Erreur {response.status_code} : {text}")
                return OrderSagaState.INCREASING_STOCK

        except Exception as e:
            self.logger.error("La création d'une transaction de paiement a échoué : " + str(e))
            return OrderSagaState.INCREASING_STOCK

    def rollback(self):
        """Call payment microservice to delete payment transaction"""
        try:
            response = requests.delete(f'{config.API_GATEWAY_URL}/store-manager-api/payments/order/{self.order_id}')
            if response.ok:
                self.logger.debug("La suppression d'une transaction de paiement a réussi")
                return OrderSagaState.INCREASING_STOCK
            else:
                text = response.json()
                self.logger.error(f"Erreur {response.status_code} : {text}")
                return OrderSagaState.INCREASING_STOCK
        except Exception as e:
            self.logger.error("La suppression d'une transaction de paiement a échoué : " + str(e))
            return OrderSagaState.INCREASING_STOCK