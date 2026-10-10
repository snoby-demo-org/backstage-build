import dagger
from dagger import dag, function, object_type


@object_type
class BackstageBuild:
    """Build the Backstage app image through the shared Dagger engine.

    Runs the repo's Dockerfile (packages/backend/Dockerfile) through
    dag.docker_build() so every build layer is cached in the node-local Dagger
    engine (/var/lib/dagger on the worker node). On self-hosted ARC runners that
    cache persists across CI runs, giving warm rebuilds without Dagger Cloud.
    """

    @function
    async def build(
        self,
        source: dagger.Directory,
        image_ref: str,
        yarn_token: dagger.Secret,
        dockerfile: str = "packages/backend/Dockerfile",
        platform: str = "linux/amd64",
    ) -> str:
        """Build and publish the Backstage image.

        Args:
            source: the checked-out repository root.
            image_ref: full registry ref to publish to.
            yarn_token: GitHub token used as YARN_NPM_AUTH_TOKEN build-arg.
            dockerfile: path (relative to source) of the Dockerfile.
            platform: target platform.
        """
        secret_val = await yarn_token.plaintext()
        ctr = dag.docker_build(
            context=source,
            dockerfile=dockerfile,
            platform=platform,
            build_args=[
                {
                    "name": "YARN_NPM_AUTH_TOKEN",
                    "value": secret_val,
                }
            ],
        )
        # Build it (materialize the image) then publish.
        await ctr.sync()
        digest = await ctr.publish(address=image_ref)
        return digest
