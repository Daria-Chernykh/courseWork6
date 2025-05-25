from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from src.db.session import SAModel

class ProductToOrderAssociation(SAModel):
    __tablename__ = 'product_to_order'

    id_order = Column(Integer, ForeignKey('order.id'), primary_key=True)
    id_product = Column(Integer, ForeignKey('product.id'), primary_key=True)
    count = Column(Integer, nullable=False, default=1)

    order = relationship("Order", back_populates="product_associations")
    product = relationship("Product", back_populates="order_associations")