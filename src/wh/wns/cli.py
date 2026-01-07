"""
CLI commands for WNS identity and alias management.

Commands:
    wh identity create     - Generate a new identity
    wh identity list       - List all identities
    wh identity show       - Show identity details
    wh identity delete     - Delete an identity
    wh identity export     - Export public key

    wh alias add           - Add a local alias
    wh alias remove        - Remove an alias
    wh alias list          - List all aliases
    wh alias show          - Show alias details
"""

import click
from typing import Optional

from wh.wns.identity import WNSIdentity, WNSIdentityStore
from wh.wns.aliases import AliasStore
from wh.wns.names import NameClaim, NameClaimStore, is_valid_global_name


@click.group()
def identity() -> None:
    """
    Manage WNS identities (keypairs and addresses).

    A WNS identity is an Ed25519 keypair that generates a self-certifying
    address like wh://abc123def456.wns. The address is derived from the
    public key hash, making it cryptographically bound to your identity.

    \b
    Examples:
        # Create a new identity
        wh identity create

        # Create with a friendly name
        wh identity create --name "my-server"

        # List all identities
        wh identity list

        # Show details of an identity
        wh identity show abc123def456

        # Export public key (to share with others)
        wh identity export abc123def456
    """
    pass


@identity.command("create")
@click.option(
    "--name",
    "-n",
    default=None,
    help="Friendly name for the identity",
)
def identity_create(name: Optional[str]) -> None:
    """
    Generate a new WNS identity.

    Creates a new Ed25519 keypair and derives a self-certifying address.
    The private key is stored securely in ~/.wh/identity/<address>/.

    \b
    Example:
        $ wh identity create --name "home-server"
        Created: wh://abc123def456ghij.wns
        Name: home-server
        Keys saved to: ~/.wh/identity/abc123def456ghij/
    """
    # Generate new identity
    identity = WNSIdentity.generate(name=name)

    # Save to store
    store = WNSIdentityStore()
    path = store.save_identity(identity)

    # Display result
    click.echo(f"Created: {identity.full_address}")
    if name:
        click.echo(f"Name: {name}")
    click.echo(f"Keys saved to: {path.parent}/")
    click.echo()
    click.echo("Share this address with clients who want to connect to you.")
    click.echo("Keep your private key safe - it cannot be recovered if lost.")


@identity.command("list")
def identity_list() -> None:
    """
    List all stored WNS identities.

    \b
    Example:
        $ wh identity list
        ADDRESS                      NAME
        abc123def456ghijklmnopqrstuv my-server
        xyz789abc123defghijklmnopqrs (unnamed)
    """
    store = WNSIdentityStore()
    identities = store.list_identities()

    if not identities:
        click.echo("No identities found.")
        click.echo("Create one with: wh identity create")
        return

    # Print header
    click.echo(f"{'ADDRESS':<28} {'NAME'}")
    click.echo("-" * 50)

    for ident in identities:
        name = ident.name or "(unnamed)"
        click.echo(f"{ident.address:<28} {name}")


@identity.command("show")
@click.argument("address")
def identity_show(address: str) -> None:
    """
    Show details of a WNS identity.

    \b
    Example:
        $ wh identity show abc123def456ghij
        Address: wh://abc123def456ghij.wns
        Scoped address: wh://laptop.abc123def456ghij.wns
        Name: my-server
        Public key: LS0tLS1CRUdJTi4uLg==
        Has private key: yes
    """
    store = WNSIdentityStore()
    identity = store.load_identity(address)

    if not identity:
        raise click.ClickException(f"Identity not found: {address}")

    import base64

    click.echo(f"Address: {identity.full_address}")
    if identity.scoped_name:
        click.echo(f"Scoped address: {identity.full_scoped_address}")
    click.echo(f"Name: {identity.name or '(unnamed)'}")
    if identity.scoped_name:
        click.echo(f"Scoped name: {identity.scoped_name}")
    click.echo(f"Public key: {base64.b64encode(identity.public_key).decode('ascii')}")
    click.echo(f"Has private key: {'yes' if identity.can_sign else 'no'}")


@identity.command("delete")
@click.argument("address")
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt",
)
def identity_delete(address: str, yes: bool) -> None:
    """
    Delete a WNS identity.

    WARNING: This permanently deletes the private key. The address will
    no longer be usable. This action cannot be undone.

    \b
    Example:
        $ wh identity delete abc123def456ghij
        Are you sure you want to delete abc123def456ghij? [y/N]: y
        Deleted.
    """
    store = WNSIdentityStore()

    # Check it exists
    identity = store.load_identity(address)
    if not identity:
        raise click.ClickException(f"Identity not found: {address}")

    # Confirm deletion
    if not yes:
        click.echo(f"WARNING: This will permanently delete the identity and private key.")
        click.echo(f"Address: {identity.full_address}")
        if not click.confirm("Are you sure?"):
            click.echo("Cancelled.")
            return

    # Delete
    if store.delete_identity(address):
        click.echo("Deleted.")
    else:
        raise click.ClickException("Failed to delete identity")


@identity.command("export")
@click.argument("address")
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Output file (default: stdout)",
)
def identity_export(address: str, output: Optional[str]) -> None:
    """
    Export the public key of an identity.

    Exports the public key in a format that can be shared with others
    for verification purposes. This does NOT export the private key.

    \b
    Example:
        $ wh identity export abc123def456ghij
        {
          "address": "abc123def456ghij",
          "public_key": "LS0tLS1CRUdJTi4uLg=="
        }

        # Save to file
        $ wh identity export abc123def456ghij -o server.pub
    """
    store = WNSIdentityStore()
    identity = store.load_identity(address)

    if not identity:
        raise click.ClickException(f"Identity not found: {address}")

    import base64
    import json

    data = {
        "address": identity.address,
        "full_address": identity.full_address,
        "public_key": base64.b64encode(identity.public_key).decode("ascii"),
        "name": identity.name,
    }

    json_str = json.dumps(data, indent=2)

    if output:
        with open(output, "w") as f:
            f.write(json_str)
        click.echo(f"Exported to: {output}")
    else:
        click.echo(json_str)


@identity.command("set-name")
@click.argument("address")
@click.argument("scoped_name")
def identity_set_name(address: str, scoped_name: str) -> None:
    """
    Set or update the scoped name for an identity.

    Scoped names let you publish a human-readable name for your identity.
    The full address becomes: wh://name.address.wns

    Unlike global names, scoped names are bound to your cryptographic
    identity, so there are no collisions - anyone can use any name.

    \b
    Example:
        $ wh identity set-name abc123def456ghij laptop
        Scoped name set: wh://laptop.abc123def456ghij.wns

        # Others can now connect using:
        $ wh ssh wh://laptop.abc123def456ghij.wns
    """
    store = WNSIdentityStore()
    identity = store.load_identity(address)

    if not identity:
        raise click.ClickException(f"Identity not found: {address}")

    # Validate scoped name
    if not scoped_name.replace("-", "").replace("_", "").isalnum():
        raise click.ClickException(
            "Invalid scoped name. Use alphanumeric characters, dashes, or underscores."
        )

    if len(scoped_name) > 32:
        raise click.ClickException("Scoped name must be 32 characters or less.")

    identity.scoped_name = scoped_name.lower()
    store.save_identity(identity)

    click.echo(f"Scoped name set: {identity.full_scoped_address}")
    click.echo()
    click.echo("Clients can now connect using this address.")
    click.echo("The scoped name will be published in your code advertisements.")


@identity.command("claim-name")
@click.argument("name")
@click.option(
    "-i", "--identity",
    "address",
    default=None,
    help="Identity address to use (default: first identity)",
)
def identity_claim_name(name: str, address: Optional[str]) -> None:
    """
    Claim a global name for your identity.

    Global names are first-come-first-served. Once claimed, the name
    points to your identity's current code advertisement.

    The name becomes: wh://name.wns (no address suffix)

    WARNING: Global names can be squatted. For security-critical
    applications, use scoped names or verify the public key.

    \b
    Example:
        $ wh identity claim-name my-laptop
        Claimed: wh://my-laptop.wns -> abc123def456ghij

        # Others can now connect using:
        $ wh ssh wh://my-laptop.wns
    """
    # Validate name
    if not is_valid_global_name(name):
        raise click.ClickException(
            f"Invalid name: {name}. Use alphanumeric characters, dashes, or underscores. "
            f"Max 32 characters. Cannot be a reserved name."
        )

    # Load identity
    id_store = WNSIdentityStore()
    if address:
        identity = id_store.load_identity(address)
        if not identity:
            raise click.ClickException(f"Identity not found: {address}")
    else:
        identity = id_store.get_default_identity()
        if not identity:
            raise click.ClickException(
                "No identity found. Create one with: wh identity create"
            )

    # Create claim
    claim = NameClaim.create(identity, name)

    # Save locally
    name_store = NameClaimStore()
    name_store.save_claim(claim)

    click.echo(f"Claimed: wh://{claim.name}.wns -> {claim.address}")
    click.echo()
    click.echo("Note: This claim is stored locally. To publish it to the DHT,")
    click.echo("run 'wh serve' which will automatically publish your name claims.")
    click.echo()
    click.echo(f"Claim expires: {claim.expires.isoformat()}")
    click.echo("Run this command again to renew the claim before expiry.")


@identity.command("list-names")
def identity_list_names() -> None:
    """
    List all claimed global names.

    \b
    Example:
        $ wh identity list-names
        NAME         ADDRESS                      EXPIRES
        my-laptop    abc123def456ghij...          2024-01-22T10:30:00
        work-server  xyz789abc123def...           2024-01-25T15:45:00
    """
    name_store = NameClaimStore()
    claims = name_store.list_claims()

    if not claims:
        click.echo("No names claimed.")
        click.echo("Claim one with: wh identity claim-name <name>")
        return

    # Print header
    click.echo(f"{'NAME':<16} {'ADDRESS':<28} {'STATUS'}")
    click.echo("-" * 60)

    for claim in claims:
        if claim.is_expired():
            status = "EXPIRED"
        else:
            days = claim.time_remaining() / (24 * 60 * 60)
            status = f"{days:.1f} days remaining"
        click.echo(f"{claim.name:<16} {claim.address:<28} {status}")


@identity.command("release-name")
@click.argument("name")
@click.option(
    "--yes", "-y",
    is_flag=True,
    help="Skip confirmation prompt",
)
def identity_release_name(name: str, yes: bool) -> None:
    """
    Release a claimed global name.

    This removes the name claim from local storage. The name may be
    claimed by someone else after it expires in the DHT.

    \b
    Example:
        $ wh identity release-name my-laptop
        Released: my-laptop
    """
    name_store = NameClaimStore()
    claim = name_store.load_claim(name)

    if not claim:
        raise click.ClickException(f"Name not found: {name}")

    if not yes:
        click.echo(f"This will release the name claim for: wh://{claim.name}.wns")
        if not click.confirm("Are you sure?"):
            click.echo("Cancelled.")
            return

    name_store.delete_claim(name)
    click.echo(f"Released: {name}")


@identity.command("import")
@click.argument("file", type=click.Path(exists=True))
def identity_import(file: str) -> None:
    """
    Import a public key as a known host.

    This adds the public key to your known_hosts, allowing you to verify
    servers you connect to.

    \b
    Example:
        $ wh identity import server.pub
        Added to known hosts: wh://abc123def456ghij.wns
    """
    import json

    with open(file) as f:
        data = json.load(f)

    import base64
    public_key = base64.b64decode(data["public_key"])
    identity = WNSIdentity.from_public_key(public_key)
    identity.name = data.get("name")

    store = WNSIdentityStore()
    path = store.save_known_host(identity)

    click.echo(f"Added to known hosts: {identity.full_address}")
    if identity.name:
        click.echo(f"Name: {identity.name}")
    click.echo(f"Saved to: {path}")


# =============================================================================
# Alias Commands
# =============================================================================


@click.group()
def alias() -> None:
    """
    Manage local aliases for WNS addresses.

    Aliases let you assign memorable names to WNS addresses, similar to
    SSH config host aliases. Aliases are stored locally in ~/.wh/aliases.json.

    \b
    Examples:
        # Add an alias
        wh alias add laptop wh://abc123def456.wns

        # Add with description and default username
        wh alias add work-server wh://xyz789.wns -d "Office server" -u admin

        # Use the alias (works in all commands)
        wh ssh laptop
        wh scp laptop:/file.txt .

        # List all aliases
        wh alias list

        # Remove an alias
        wh alias remove laptop
    """
    pass


@alias.command("add")
@click.argument("name")
@click.argument("address")
@click.option(
    "-d", "--description",
    default=None,
    help="Description for this alias",
)
@click.option(
    "-u", "--username",
    default=None,
    help="Default username for this alias",
)
@click.option(
    "-f", "--force",
    is_flag=True,
    help="Overwrite existing alias",
)
def alias_add(
    name: str,
    address: str,
    description: Optional[str],
    username: Optional[str],
    force: bool,
) -> None:
    """
    Add a local alias for a WNS address.

    \b
    Examples:
        # Simple alias
        $ wh alias add laptop wh://abc123def456ghij.wns
        Added: laptop -> wh://abc123def456ghij.wns

        # With description and username
        $ wh alias add server wh://xyz.wns -d "Production server" -u admin
        Added: server -> wh://xyz.wns

        # Update existing alias
        $ wh alias add laptop wh://newaddress.wns --force
    """
    store = AliasStore()

    try:
        store.add(
            name=name,
            address=address,
            description=description,
            username=username,
            overwrite=force,
        )
    except ValueError as e:
        raise click.ClickException(str(e))

    alias = store.get(name)
    click.echo(f"Added: {name} -> {alias.address}")
    if description:
        click.echo(f"Description: {description}")
    if username:
        click.echo(f"Default username: {username}")


@alias.command("remove")
@click.argument("name")
def alias_remove(name: str) -> None:
    """
    Remove an alias.

    \b
    Example:
        $ wh alias remove laptop
        Removed: laptop
    """
    store = AliasStore()

    if not store.remove(name):
        raise click.ClickException(f"Alias not found: {name}")

    click.echo(f"Removed: {name}")


@alias.command("list")
def alias_list() -> None:
    """
    List all local aliases.

    \b
    Example:
        $ wh alias list
        NAME          ADDRESS                               DESCRIPTION
        laptop        wh://abc123def456ghij.wns             My laptop
        work-server   wh://xyz789abc123defg.wns             Office server
    """
    store = AliasStore()
    aliases = store.list()

    if not aliases:
        click.echo("No aliases defined.")
        click.echo("Add one with: wh alias add <name> <address>")
        return

    # Calculate column widths
    name_width = max(len(a.name) for a in aliases)
    name_width = max(name_width, 4)  # Minimum "NAME"

    addr_width = max(len(a.address) for a in aliases)
    addr_width = max(addr_width, 7)  # Minimum "ADDRESS"

    # Print header
    click.echo(f"{'NAME':<{name_width}}  {'ADDRESS':<{addr_width}}  DESCRIPTION")
    click.echo("-" * (name_width + addr_width + 20))

    for a in aliases:
        desc = a.description or ""
        if a.username:
            desc = f"[{a.username}@] {desc}".strip()
        click.echo(f"{a.name:<{name_width}}  {a.address:<{addr_width}}  {desc}")


@alias.command("show")
@click.argument("name")
def alias_show(name: str) -> None:
    """
    Show details of an alias.

    \b
    Example:
        $ wh alias show laptop
        Name: laptop
        Address: wh://abc123def456ghij.wns
        Description: My personal laptop
        Default username: admin
    """
    store = AliasStore()
    a = store.get(name)

    if not a:
        raise click.ClickException(f"Alias not found: {name}")

    click.echo(f"Name: {a.name}")
    click.echo(f"Address: {a.address}")
    if a.description:
        click.echo(f"Description: {a.description}")
    if a.username:
        click.echo(f"Default username: {a.username}")


@alias.command("resolve")
@click.argument("name")
def alias_resolve(name: str) -> None:
    """
    Resolve an alias to its WNS address.

    Useful for scripting or debugging.

    \b
    Example:
        $ wh alias resolve laptop
        wh://abc123def456ghij.wns

        # Use in scripts
        $ ADDRESS=$(wh alias resolve laptop)
    """
    store = AliasStore()
    address = store.resolve(name)

    if not address:
        raise click.ClickException(f"Could not resolve: {name}")

    click.echo(address)
