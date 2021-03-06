import logging
from datetime import datetime
from flask_babel import gettext
from sqlalchemy.dialects.postgresql import JSONB
from followthemoney import model
from followthemoney.types import registry
from followthemoney.exc import InvalidData

from aleph.core import db
from aleph.model.collection import Collection
from aleph.model.common import SoftDeleteModel
from aleph.model.common import iso_text, make_textid, ENTITY_ID_LEN

log = logging.getLogger(__name__)


class Entity(db.Model, SoftDeleteModel):
    THING = 'Thing'
    LEGAL_ENTITY = 'LegalEntity'

    id = db.Column(db.String(ENTITY_ID_LEN), primary_key=True,
                   default=make_textid, nullable=False, unique=False)
    schema = db.Column(db.String(255), index=True)
    data = db.Column('data', JSONB)

    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=True)  # noqa
    collection_id = db.Column(db.Integer, db.ForeignKey('collection.id'), index=True)  # noqa
    collection = db.relationship(Collection, backref=db.backref('entities', lazy='dynamic'))  # noqa

    @property
    def model(self):
        return model.get(self.schema)

    def undelete(self):
        self.deleted_at = None
        db.session.add(self)

    def update(self, data, collection, validate=True):
        proxy = model.get_proxy(data, cleaned=False)
        if validate:
            # This isn't strictly required because the proxy will contain
            # only those values that can be inserted for each property,
            # making it valid -- all this does, therefore, is to raise an
            # exception that notifies the user.
            proxy.schema.validate(data)
        proxy = collection.ns.apply(proxy)
        self.id = collection.ns.sign(self.id)
        self.schema = proxy.schema.name
        previous = self.to_proxy()
        for prop in proxy.schema.properties.values():
            # Do not allow the user to overwrite hashes because this could
            # lead to a user accessing random objects.
            if prop.type == registry.checksum:
                prev = previous.get(prop)
                proxy.set(prop, prev, cleaned=True, quiet=True)
        self.data = proxy.properties
        self.updated_at = datetime.utcnow()
        self.deleted_at = None
        db.session.add(self)

    def to_proxy(self):
        return model.get_proxy({
            'id': self.id,
            'schema': self.schema,
            'properties': self.data,
            'created_at': iso_text(self.created_at),
            'updated_at': iso_text(self.updated_at),
            'role_id': self.role_id,
            'mutable': True
        })

    @classmethod
    def create(cls, data, collection, role_id=None, validate=True):
        entity = cls()
        entity_id = data.get('id') or make_textid()
        if not registry.entity.validate(entity_id):
            raise InvalidData(gettext("Invalid entity ID"))
        entity.id = collection.ns.sign(entity_id)
        entity.collection_id = collection.id
        entity.role_id = role_id
        entity.update(data, collection, validate=validate)
        return entity

    @classmethod
    def by_id(cls, entity_id, collection=None, deleted=False):
        q = cls.all(deleted=deleted)
        q = q.filter(cls.id == entity_id)
        if collection is not None:
            q = q.filter(cls.collection_id == collection.id)
        return q.first()

    @classmethod
    def by_collection(cls, collection_id):
        q = cls.all()
        q = q.filter(Entity.collection_id == collection_id)
        q = q.yield_per(5000)
        return q

    @classmethod
    def delete_by_collection(cls, collection_id, deleted_at):
        pq = db.session.query(cls)
        pq = pq.filter(cls.collection_id == collection_id)
        pq = pq.filter(cls.deleted_at == None)  # noqa
        pq.update({cls.deleted_at: deleted_at},
                  synchronize_session=False)

    def __repr__(self):
        return '<Entity(%r, %r)>' % (self.id, self.schema)
