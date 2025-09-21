# catalog/migrations/0005_size_alter_product_size.py
from django.db import migrations, models
import django.db.models.deletion


def seed_sizes(apps, schema_editor):
    Size = apps.get_model("catalog", "Size")
    data = [
        ("s", "S", 1),
        ("m", "M", 2),
        ("l", "L", 3),
        ("xl", "XL", 4),
        ("xxl", "XXL", 5),
        ("xxxl", "XXXL", 6),
    ]
    for slug, label, order in data:
        Size.objects.update_or_create(
            slug=slug,
            defaults={"label": label, "order": order, "is_active": True},
        )


def copy_text_size_to_fk(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    Size = apps.get_model("catalog", "Size")

    # žemėlapiai pagal slug/label (mažosiomis)
    sizes = list(Size.objects.all())
    by_label = {s.label.lower(): s for s in sizes}
    by_slug = {s.slug.lower(): s for s in sizes}

    # persikeliam seną tekstinį 'size' į naują 'size_fk'
    for p in Product.objects.all():
        t = (getattr(p, "size", "") or "").strip().lower()
        if not t:
            continue
        s = by_slug.get(t) or by_label.get(t)
        if s:
            # rašom tiesiai į fk_id, kad nekviesčiau papildomų query
            setattr(p, "size_fk_id", s.id)
            p.save(update_fields=["size_fk"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        # TIKSLUS tavo 0004 failo vardas:
        ("catalog", "0004_product_price_product_size_product_stock"),
    ]

    operations = [
        # 1) Sukuriam Size žodyną
        migrations.CreateModel(
            name="Size",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=40, unique=True)),
                ("label", models.CharField(max_length=40)),
                ("order", models.PositiveSmallIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ["order", "label"]},
        ),

        # 2) Pridedam LAIKINĄ FK lauką prie Product
        migrations.AddField(
            model_name="product",
            name="size_fk",
            field=models.ForeignKey(
                to="catalog.size",
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="products",
                db_index=True,
            ),
        ),

        # 3) Įterpiam standartinius dydžius
        migrations.RunPython(seed_sizes, reverse_code=noop),

        # 4) Perkopijuojam seną tekstinį 'size' -> 'size_fk'
        migrations.RunPython(copy_text_size_to_fk, reverse_code=noop),

        # 5) Pašalinam seną CharField 'size'
        migrations.RemoveField(model_name="product", name="size"),

        # 6) Pervadinam 'size_fk' -> 'size'
        migrations.RenameField(model_name="product", old_name="size_fk", new_name="size"),
    ]
