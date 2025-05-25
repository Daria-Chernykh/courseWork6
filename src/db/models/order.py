from sqlalchemy import Table, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from src.db.session import SAModel
from src.db.models.product_to_order_association import ProductToOrderAssociation

class Order(SAModel):
    __tablename__ = "order"

    id = Column(Integer, primary_key=True, autoincrement=True)
    open_date = Column(DateTime, default=datetime.now, nullable=False)
    close_date = Column(DateTime)
    id_status = Column(Integer, ForeignKey("status.id"), nullable=False)
    status = relationship("Status", foreign_keys=id_status)
    id_operator = Column(Integer, ForeignKey("user.id"))
    operator = relationship("User", foreign_keys=id_operator)
    note = Column(String)
    customer = Column(String, nullable=False)
    delivery_info = Column(String)

    # Связь с продуктами через ассоциативную таблицу
    product_associations = relationship("ProductToOrderAssociation", back_populates="order")
    products = relationship("Product", secondary="product_to_order", back_populates="orders", overlaps="order_associations")

    def get_product_summary(self):
        summary = {}
        for assoc in self.product_associations:
            product = assoc.product
            count = assoc.count
            if product.name in summary:
                summary[product.name] += count
            else:
                summary[product.name] = count
        return summary

    def get_product_string(self):
        summary = self.get_product_summary()
        return ", ".join(f"{name} ({qty})" for name, qty in summary.items())
