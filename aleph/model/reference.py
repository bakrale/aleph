import logging

from aleph.core import db
from aleph.model.entity import Entity
from aleph.model.document import Document
from aleph.model.common import DatedModel


log = logging.getLogger(__name__)


class Reference(db.Model, DatedModel):
    id = db.Column(db.Integer(), primary_key=True)
    document_id = db.Column(db.BigInteger, db.ForeignKey('document.id'))
    entity_id = db.Column(db.Integer, db.ForeignKey('entity.id'))
    weight = db.Column(db.Integer)

    entity = db.relationship(Entity, backref=db.backref('references',
                             lazy='dynamic', cascade='all, delete-orphan'))
    document = db.relationship(Document, backref=db.backref('references',
                               lazy='dynamic', cascade='all, delete-orphan'))

    @classmethod
    def delete_document(cls, document_id):
        q = cls.all().filter_by(document_id=document_id)
        q.delete(synchronize_session='fetch')

    def __repr__(self):
        return '<Reference(%r, %r)>' % (self.document_id, self.entity_id)
