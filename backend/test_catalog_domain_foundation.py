from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

import models
import schemas
from conftest import make_producto, make_tenant, make_user


def _catalog(db, tenant, suffix="catalogo"):
    catalog = models.CatalogSite(
        tenant_id=tenant.id,
        slug=f"catalogo-{suffix}",
        display_name=f"Catalogo {suffix}",
        theme_config={"primaryColor": "#2563EB"},
    )
    db.add(catalog)
    db.commit()
    db.refresh(catalog)
    return catalog


def test_catalog_domain_is_tenant_scoped_and_never_auto_publishes_product(db_session):
    tenant_a = make_tenant(db_session, "801")
    tenant_b = make_tenant(db_session, "802")
    product_a = make_producto(db_session, tenant_a, "801")
    catalog_a = _catalog(db_session, tenant_a, "a")
    catalog_b = _catalog(db_session, tenant_b, "b")

    item = models.CatalogItem(
        tenant_id=tenant_a.id,
        catalog_id=catalog_a.id,
        product_id=product_a.id,
        kind="internal_product",
        public_name="Nombre publico independiente",
        slug="nombre-publico-independiente",
        price_mode="quotation",
        price_source="manual",
        availability_source="manual",
        availability_status="consult",
        minimum_quantity=Decimal("1"),
    )
    db_session.add(item)
    db_session.commit()

    assert product_a.catalog_items == [item]
    assert item.published is False
    assert db_session.query(models.CatalogItem).filter(
        models.CatalogItem.tenant_id == tenant_b.id,
        models.CatalogItem.catalog_id == catalog_b.id,
    ).count() == 0


def test_catalog_slug_and_entitlement_are_unique_per_expected_scope(db_session):
    tenant = make_tenant(db_session, "803")
    user = make_user(db_session, tenant, email="catalog-803@example.com")
    _catalog(db_session, tenant, "unico")

    duplicate = models.CatalogSite(
        tenant_id=tenant.id,
        slug="otro-slug",
        display_name="Duplicado",
        theme_config={},
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    db_session.add(models.TenantProductEntitlement(
        tenant_id=tenant.id,
        product_code=models.CATALOG_PRODUCT_CODE,
        configured_by_user_id=user.id,
    ))
    db_session.commit()
    db_session.add(models.TenantProductEntitlement(
        tenant_id=tenant.id,
        product_code=models.CATALOG_PRODUCT_CODE,
        configured_by_user_id=user.id,
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_catalog_schema_normalizes_slug_and_rejects_invalid_sync_combinations():
    site = schemas.CatalogSiteCreate(slug="Papelería G&YP", display_name="Papelería G&YP")
    assert site.slug == "papeleria-g-yp"

    with pytest.raises(ValueError, match="precio sincronizado"):
        schemas.CatalogItemCreate(
            public_name="Bolsa kraft",
            slug="bolsa-kraft",
            price_source="product",
        )

    with pytest.raises(ValueError, match="price_min no puede"):
        schemas.CatalogItemCreate(
            public_name="Bolsa kraft",
            slug="bolsa-kraft",
            price_mode="range",
            price_min=Decimal("80"),
            price_max=Decimal("50"),
        )
