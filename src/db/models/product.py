from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from src.db.session import SAModel

class Product(SAModel):
    __tablename__ = "product"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)

    orders = relationship("Order", secondary="product_to_order", back_populates="products", overlaps="order_associations")
    order_associations = relationship("ProductToOrderAssociation", back_populates="product")