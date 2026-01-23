"""
wh namespace - Manage enterprise namespaces for multi-tenancy.

Commands for creating, listing, and managing namespaces.
"""

import click
from typing import Optional


@click.group("namespace")
def namespace():
    """
    Manage enterprise namespaces (multi-tenancy).

    Namespaces provide isolation between different teams or tenants,
    with separate DHT prefixes and optional access controls.

    \b
    Examples:
        wh namespace create engineering --description "Engineering team"
        wh namespace list
        wh namespace add-member engineering user@example.com
        wh --namespace=engineering listen --ssh
    """
    pass


@namespace.command("create")
@click.argument("name")
@click.option(
    "--description", "-d",
    help="Description of the namespace"
)
@click.option(
    "--public/--private",
    default=False,
    help="Whether namespace is public (anyone can join)"
)
@click.option(
    "--max-members",
    type=int,
    help="Maximum number of members"
)
@click.option(
    "--admin",
    multiple=True,
    help="Admin identity address (can specify multiple)"
)
def create(
    name: str,
    description: Optional[str],
    public: bool,
    max_members: Optional[int],
    admin: tuple,
):
    """
    Create a new namespace.

    NAME is the unique identifier for the namespace.

    \b
    Examples:
        wh namespace create engineering
        wh namespace create sales --description "Sales team namespace"
        wh namespace create public-demo --public
        wh namespace create limited --max-members 10
    """
    from wh.enterprise.namespace import get_namespace_manager, NamespaceExistsError

    try:
        manager = get_namespace_manager()
        ns = manager.create(
            name=name,
            description=description,
            public=public,
            max_members=max_members,
            admins=list(admin),
        )

        click.echo(f"Created namespace: {ns.name}")
        click.echo(f"  DHT prefix: {ns.dht_prefix}")
        if ns.description:
            click.echo(f"  Description: {ns.description}")
        if ns.public:
            click.echo("  Access: public")
        if ns.max_members:
            click.echo(f"  Max members: {ns.max_members}")

    except NamespaceExistsError:
        raise click.ClickException(f"Namespace '{name}' already exists")
    except ValueError as e:
        raise click.ClickException(str(e))


@namespace.command("list")
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Output as JSON"
)
def list_namespaces(as_json: bool):
    """
    List all namespaces.

    \b
    Examples:
        wh namespace list
        wh namespace list --json
    """
    import json
    from wh.enterprise.namespace import get_namespace_manager

    manager = get_namespace_manager()
    namespaces = manager.list()

    if as_json:
        data = [ns.to_dict() for ns in namespaces]
        click.echo(json.dumps(data, indent=2))
    else:
        if not namespaces:
            click.echo("No namespaces found")
            return

        for ns in namespaces:
            status = "public" if ns.public else "private"
            members = len(ns.members) + len(ns.admins)
            click.echo(f"{ns.name} ({status}) - {members} members")
            if ns.description:
                click.echo(f"  {ns.description}")


@namespace.command("show")
@click.argument("name")
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Output as JSON"
)
def show(name: str, as_json: bool):
    """
    Show details for a namespace.

    \b
    Examples:
        wh namespace show engineering
        wh namespace show engineering --json
    """
    import json
    from wh.enterprise.namespace import get_namespace_manager, NamespaceNotFoundError

    try:
        manager = get_namespace_manager()
        ns = manager.get(name)

        if as_json:
            click.echo(json.dumps(ns.to_dict(), indent=2))
        else:
            click.echo(f"Name: {ns.name}")
            click.echo(f"DHT Prefix: {ns.dht_prefix}")
            click.echo(f"Created: {ns.created_at}")
            if ns.description:
                click.echo(f"Description: {ns.description}")
            click.echo(f"Public: {'yes' if ns.public else 'no'}")
            if ns.max_members:
                click.echo(f"Max Members: {ns.max_members}")
            click.echo(f"Admins: {', '.join(ns.admins) if ns.admins else 'none'}")
            click.echo(f"Members: {', '.join(ns.members) if ns.members else 'none'}")

    except NamespaceNotFoundError:
        raise click.ClickException(f"Namespace '{name}' not found")


@namespace.command("delete")
@click.argument("name")
@click.option(
    "--force", "-f",
    is_flag=True,
    help="Force delete even if namespace has members"
)
@click.confirmation_option(prompt="Are you sure you want to delete this namespace?")
def delete(name: str, force: bool):
    """
    Delete a namespace.

    \b
    Examples:
        wh namespace delete test-namespace
        wh namespace delete old-namespace --force
    """
    from wh.enterprise.namespace import get_namespace_manager, NamespaceNotFoundError

    try:
        manager = get_namespace_manager()
        manager.delete(name, force=force)
        click.echo(f"Deleted namespace: {name}")

    except NamespaceNotFoundError:
        raise click.ClickException(f"Namespace '{name}' not found")
    except ValueError as e:
        raise click.ClickException(str(e))


@namespace.command("add-admin")
@click.argument("name")
@click.argument("identity")
def add_admin(name: str, identity: str):
    """
    Add an admin to a namespace.

    \b
    Examples:
        wh namespace add-admin engineering admin@example.com
    """
    from wh.enterprise.namespace import get_namespace_manager, NamespaceNotFoundError

    try:
        manager = get_namespace_manager()
        ns = manager.add_admin(name, identity)
        click.echo(f"Added admin '{identity}' to namespace '{name}'")

    except NamespaceNotFoundError:
        raise click.ClickException(f"Namespace '{name}' not found")


@namespace.command("remove-admin")
@click.argument("name")
@click.argument("identity")
def remove_admin(name: str, identity: str):
    """
    Remove an admin from a namespace.

    \b
    Examples:
        wh namespace remove-admin engineering old-admin@example.com
    """
    from wh.enterprise.namespace import get_namespace_manager, NamespaceNotFoundError

    try:
        manager = get_namespace_manager()
        ns = manager.remove_admin(name, identity)
        click.echo(f"Removed admin '{identity}' from namespace '{name}'")

    except NamespaceNotFoundError:
        raise click.ClickException(f"Namespace '{name}' not found")


@namespace.command("add-member")
@click.argument("name")
@click.argument("identity")
def add_member(name: str, identity: str):
    """
    Add a member to a namespace.

    \b
    Examples:
        wh namespace add-member engineering developer@example.com
    """
    from wh.enterprise.namespace import get_namespace_manager, NamespaceNotFoundError

    try:
        manager = get_namespace_manager()
        ns = manager.add_member(name, identity)
        click.echo(f"Added member '{identity}' to namespace '{name}'")

    except NamespaceNotFoundError:
        raise click.ClickException(f"Namespace '{name}' not found")
    except ValueError as e:
        raise click.ClickException(str(e))


@namespace.command("remove-member")
@click.argument("name")
@click.argument("identity")
def remove_member(name: str, identity: str):
    """
    Remove a member from a namespace.

    \b
    Examples:
        wh namespace remove-member engineering former-developer@example.com
    """
    from wh.enterprise.namespace import get_namespace_manager, NamespaceNotFoundError

    try:
        manager = get_namespace_manager()
        ns = manager.remove_member(name, identity)
        click.echo(f"Removed member '{identity}' from namespace '{name}'")

    except NamespaceNotFoundError:
        raise click.ClickException(f"Namespace '{name}' not found")
