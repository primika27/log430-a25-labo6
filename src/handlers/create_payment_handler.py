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
            # Récupérer le montant total de la commande et le user_id
            response = requests.get(f'{config.API_GATEWAY_URL}/store-manager-api/orders/{self.order_id}')
            if response.ok:
                data = response.json()
                self.total_amount = data.get("total_amount", 0)
                user_id = data.get("user_id")
                
                if not user_id:
                    self.logger.error("user_id manquant dans les données de la commande")
                    return OrderSagaState.INCREASING_STOCK
            else:
                text = response.json()
                self.logger.error(f"Erreur {response.status_code} lors de la récupération du montant total : {text}")
                return OrderSagaState.INCREASING_STOCK

            # Créer une transaction de paiement via l'API Gateway
            response = requests.post(f'{config.API_GATEWAY_URL}/payments-api/payments',
                json={
                    "order_id": self.order_id,
                    "user_id": user_id,
                    "total_amount": self.total_amount
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